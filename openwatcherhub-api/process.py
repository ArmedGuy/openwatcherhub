import typing

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


def download(ctx: ProcessContext, product_instance):
    bands = ctx.setup["input"]["bands"]
    folder = BASE_URL + product_instance["S3Path"] + "/"
    url = folder + ctx.product["granules"]["granuleFile"]
    print(url)
    def_file = requests.get(url).text
    granules = IMAGE_FILE_RE.findall(def_file)
    matched_granules = ctx.product["granules"]["matching"](bands, granules)

    for band in bands:
        granule = [gran for gran in matched_granules if f"_{band}" in gran][0]
        url = folder + granule + FILE_EXT
        download_file(url, f"{ctx.temp_dir}/{band}{FILE_EXT}")


class PixelProcessor:
    def __init__(self, pixelFn, sampleHolder, bands):
        self.pixelFn = pixelFn
        self.bands = bands
        self.sample = sampleHolder(bands)

    def process(self, slice):
        self.sample.update(slice)
        return self.pixelFn(self.sample)

def _get_features(gdf):
    """Function to parse features from GeoDataFrame in such a manner that rasterio wants them"""
    import json
    return [json.loads(gdf.to_json())['features'][0]['geometry']]

def rerender(ctx):
    points = ctx.request.input.bounds.bbox
    bbox = box(points[0], points[1], points[2], points[3])
    geo = gpd.GeoDataFrame({'geometry': bbox}, index=[0])
    dst_crs = 'EPSG:4326'
    geo.crs = dst_crs

    bands = ctx.setup["input"]["bands"]
    srcs = [
        rasterio.open(ctx.temp_dir + "/" + band + FILE_EXT, driver='JP2OpenJPEG')
        for band in bands
    ]
    count = ctx.setup["output"]["bands"]
    sampleType = ctx.setup['output']["sampleType"]
    wanted_dtype = sample_type_to_dtype[sampleType]
    output_loc = ctx.temp_dir + "/" + "output.tiff"

    # project to WSG84
    unproj = srcs[0]
    transform, new_width, new_height = calculate_default_transform(
        unproj.crs, dst_crs, unproj.width, unproj.height, *unproj.bounds)
    kwargs = unproj.meta.copy()
    kwargs.update({
        'crs': dst_crs,
        'transform': transform,
        'width': new_width,
        'height': new_height,
        'count': len(bands),
        'dtype': np.float32,
        'driver': 'Gtiff'
    })

    with MemoryFile() as proj_bands:
        band_shp = (new_height, new_width)
        with proj_bands.open(**kwargs) as dst:
            for i in range(0, len(bands)):
                band = bands[i]
                dest = np.zeros(band_shp)
                reproject(
                    source=rasterio.band(srcs[i], 1),
                    destination=dest,
                    src_transform=unproj.transform,
                    src_crs=unproj.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest)
                # convert band data to common format
                band_def = ctx.product["bands"][band]
                input_unit = ctx.setup["input"]["units"][i]
                input_unit = band_def["defaultUnit"] if input_unit == "DEFAULT" or input_unit not in band_def["units"] else input_unit
                dest = band_def["units"][input_unit]["convert"](dest.astype(np.float32))

                dst.write(dest, i+1)
        with proj_bands.open() as src:
            data, transform = rasterio.mask.mask(src, shapes=_get_features(geo), all_touched=True, crop=True, filled=True)
            data = data.astype(np.float32)
            # do per-pixel preprocessing on masked data
            if ctx.evaluatePixelFunction:
                print("running evalscript")
                px = PixelProcessor(
                    ctx.evaluatePixelFunction,
                    ctx.product["sampleHolder"],
                    bands
                )
                data = np.apply_along_axis(px.process, 0, data)
            # write output
            with rasterio.open(
                output_loc, 
                "w", 
                driver="Gtiff", 
                width=ctx.request.output.width, 
                height=ctx.request.output.height, 
                count=count, 
                crs=dst_crs, 
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
    # Clean up open bands
    for src in srcs:
        src.close()