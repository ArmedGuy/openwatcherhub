import typing

import asyncio
import requests
import re
import rasterio
import rasterio.mask
from rasterio.io import MemoryFile
from rasterio.warp import calculate_default_transform, reproject, Resampling
import numpy as np
import geopandas as gpd
import os
from shapely.geometry import box
import time


import subprocess

class ProcessContext:
    def __init__(self, req):
        self.request = req
        self.setup = {}
        self.product = None
        self.evaluatePixelFunction = None
        self.temp_dir = ""

sample_type_to_dtype = {
    "UINT8": np.uint8,
    "UINT16": np.uint16,
    "AUTO": np.uint8
}


def download_file(url: str, dest: str):
    subprocess.run(["curl", url, "-o", dest])

BASE_URL = os.environ.get("S3_PROXY_URL", "http://127.0.0.1")
IMAGE_FILE_RE = re.compile("<IMAGE_FILE>(.*)</IMAGE_FILE>")
FILE_EXT = ".jp2"

GTIFF_DRIVER = "Gtiff"
DEST_CRS = 'EPSG:4326'


def format_setup(setup):
    # format input
    if "input" not in setup:
        raise ValueError("setup function does not return input data")
    if isinstance(setup["input"], list):
        # simple setup
        if len(setup["input"]) > 0 and isinstance(setup["input"][0], str):
            setup["input"] = {
                "bands": setup["input"],
                "units": "DEFAULT",
            }
        elif len(setup["input"]) > 0 and isinstance(setup["input"][0], dict):
            setup["input"] = setup["input"][0] # we only support one input for now
        else:
            raise ValueError("Unknown input format in evalscript")
        
        if isinstance(setup["input"]["units"], str):
            setup["input"]["units"] = [setup["input"]["units"]] * len(setup["input"]["bands"])
    else:
        raise ValueError("Invalid input definitions, expect array of string or array of one input object.")
    if "output" not in setup:
        raise ValueError("setup function does not return output data")
    if isinstance(setup["output"], list):
        raise ValueError("Only one output is currently supported!")
    setup["output"]["id"] = setup["output"].get("id", "default")
    setup["output"]["sampleType"] = setup["output"].get("sampleType", "AUTO")

    return setup


async def download(ctx: ProcessContext, product_instance):
    bands = ctx.setup["input"]["bands"]
    folder = BASE_URL + product_instance["S3Path"] + "/"
    url = folder + ctx.product["granules"]["granuleFile"]
    print(url)
    def_file = requests.get(url).text
    granules = IMAGE_FILE_RE.findall(def_file)
    matched_granules = ctx.product["granules"]["matching"](bands, granules)

    loop = asyncio.get_event_loop()
    tasks = []
    for band in bands:
        granule = [gran for gran in matched_granules if f"_{band}" in gran][0]
        url = folder + granule + FILE_EXT
        tasks.append(loop.run_in_executor(None, download_file, url, f"{ctx.temp_dir}/{band}{FILE_EXT}"))
    
    await asyncio.gather(*tasks)


class PixelProcessor:
    def __init__(self, pixelFn, sampleHolder, bands, vectorize=False):
        self.pixelFn = pixelFn
        self.bands = bands
        self.sample = sampleHolder(bands, vectorize)

    def process(self, slice):
        self.sample.update(slice)
        return self.pixelFn(self.sample)


def _get_features(gdf):
    """Function to parse features from GeoDataFrame in such a manner that rasterio wants them"""
    import json
    return [json.loads(gdf.to_json())['features'][0]['geometry']]


def rerender_band(ctx, band, band_idx):
    with rasterio.Env(GDAL_NUM_THREADS=32):
        points = ctx.request.input.bounds.bbox
        bbox = box(points[0], points[1], points[2], points[3])
        geo = gpd.GeoDataFrame({'geometry': bbox}, index=[0])
        geo.crs = DEST_CRS

        src = rasterio.open(ctx.temp_dir + "/" + band + FILE_EXT, driver='JP2OpenJPEG')
        band_output_loc = ctx.temp_dir + "/" + band + "_projmask.tiff"

        # project to WSG84
        unproj = src
        transform, new_width, new_height = calculate_default_transform(
            unproj.crs, DEST_CRS, unproj.width, unproj.height, *unproj.bounds)
        kwargs = unproj.meta.copy()
        kwargs.update({
            'crs': DEST_CRS,
            'transform': transform,
            'width': new_width,
            'height': new_height,
            'count': 1,
            'dtype': np.float32,
            'driver': GTIFF_DRIVER
        })

        with MemoryFile() as proj_band:
            band_shp = (new_height, new_width)
            with proj_band.open(**kwargs) as band_dst:
                dest = np.zeros(band_shp)
                reproject(
                    source=rasterio.band(src, 1),
                    destination=dest,
                    src_transform=unproj.transform,
                    src_crs=unproj.crs,
                    dst_transform=transform,
                    dst_crs=DEST_CRS,
                    resampling=Resampling.nearest,
                    num_threads=32,
                    warp_mem_limit=256)
                # convert band data to common format
                band_def = ctx.product["bands"][band]
                input_unit = ctx.setup["input"]["units"][band_idx]
                input_unit = band_def["defaultUnit"] if input_unit == "DEFAULT" or input_unit not in band_def["units"] else input_unit
                dest = band_def["units"][input_unit]["convert"](dest.astype(np.float32))

                band_dst.write(dest, 1)
            src.close()
            with proj_band.open() as mask_src:
                data, transform = rasterio.mask.mask(mask_src, shapes=_get_features(geo), all_touched=True, crop=True, filled=True)
                data = data.astype(np.float32)

                with rasterio.open(
                    band_output_loc, 
                    "w", 
                    driver=GTIFF_DRIVER, 
                    width=ctx.request.output.width, 
                    height=ctx.request.output.height, 
                    count=1, 
                    crs=DEST_CRS, 
                    transform=transform, 
                    dtype=np.float32
                ) as output:
                    output.write(data)
                    output.close()
                    print("wrote file to", band_output_loc)

async def render(ctx, vectorized_evalscript=False):
    bands = ctx.setup["input"]["bands"]
    loop = asyncio.get_event_loop()
    tasks = []
    start_proj_mask_time = time.time()
    for i, band in enumerate(bands):
        tasks.append(loop.run_in_executor(None, rerender_band, ctx, band, i))

    await asyncio.gather(*tasks)

    print("projection and masking took ", time.time() - start_proj_mask_time, " seconds")
    # reopen all processed and masked bands and run processing on it
    srcs = [
        rasterio.open(ctx.temp_dir + "/" + band + "_projmask.tiff", driver=GTIFF_DRIVER)
        for band in bands
    ]
    start_pixel_time = time.time()
    with rasterio.Env(GDAL_NUM_THREADS=32):
        # load data from bands into one numpy array
        data = np.stack([src.read(1) for src in srcs])
        # do per-pixel preprocessing on masked data
        if ctx.evaluatePixelFunction:
            print("running evalscript")
            vectorize = vectorized_evalscript
            px = PixelProcessor(
                ctx.evaluatePixelFunction,
                ctx.product["sampleHolder"],
                bands,
                vectorize=vectorize
            )
            if vectorize:
                data = np.stack(px.process(data))
            else:
                data = np.apply_along_axis(px.process, 0, data)
        print("pixel processing took ", time.time() - start_pixel_time, " seconds")
        # write output
        count = ctx.setup["output"]["bands"]
        sampleType = ctx.setup['output']["sampleType"]
        wanted_dtype = sample_type_to_dtype[sampleType]
        output_loc = ctx.temp_dir + "/" + "output.tiff"

        # everything is now projected to WSG84
        unproj = srcs[0]
        transform, _, _ = calculate_default_transform(
            unproj.crs, DEST_CRS, unproj.width, unproj.height, *unproj.bounds)
        with rasterio.open(
            output_loc, 
            "w", 
            driver=GTIFF_DRIVER, 
            width=ctx.request.output.width, 
            height=ctx.request.output.height, 
            count=count, 
            crs=DEST_CRS, 
            transform=transform, 
            dtype=wanted_dtype
        ) as output:
            if sampleType == "AUTO":
                print("auto mode, scaling data")
                data = data * 255
            data = data.astype(wanted_dtype)
            output.write(data)
            output.close()
            print("wrote file to", output_loc)