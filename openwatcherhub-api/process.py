import typing

import requests
import re
import rasterio
import rasterio.mask
from rasterio.io import MemoryFile
from rasterio.warp import calculate_default_transform, reproject, Resampling
import numpy as np
import geopandas as gpd
from shapely.geometry import box

import subprocess

band_definitions = {
    "sentinel-2-l2a": "MTD_MSIL2A.xml",
}

optical_band = {
    "src": np.uint16,
    "convert": lambda x: ((x - 1000) / 10000)
}

dn_band = {
    "src": np.uint8,
    "convert": lambda x: x
}

band_data_defs = {
    "sentinel-2-l2a": {
        "B01": optical_band,
        "B02": optical_band,
        "B03": optical_band,
        "B04": optical_band,
        "B05": optical_band,
        "B06": optical_band,
        "B07": optical_band,
        "B07": optical_band,
        "B08": optical_band,
        "B09": optical_band,
        "B8A": optical_band,
        "B09": optical_band,
        "B11": optical_band,
        "B12": optical_band,
        "AOT": optical_band,
        "SCL": dn_band,
        "SNW": dn_band,
        "CLD": dn_band,
        "CLP": dn_band,
        "CLM": dn_band
    }
}
resolutions = ["10m", "20m", "60m"]

sample_type_to_dtype = {
    "UINT8": np.uint8,
    "UINT16": np.uint16,
    "AUTO": np.uint8
}


def download_file(url: str, dest: str):
    subprocess.run(["curl", url, "-o", dest])

BASE_URL = "http://192.168.1.101:8080"
IMAGE_FILE_RE = re.compile("<IMAGE_FILE>(.*)</IMAGE_FILE>")
FILE_EXT = ".jp2"

def download(temp: str, s3base: str, req_type: str, bands: typing.List[str]):
    folder = BASE_URL + s3base + "/"
    url = folder + band_definitions[req_type]
    print(url)
    def_file = requests.get(url).text
    granules = IMAGE_FILE_RE.findall(def_file)
    matched_granules = []

    if req_type == "sentinel-2-l2a":
        # handle resolutions, pick the one that has all requested bands
        for res in resolutions:
            needed = [f"{band}_{res}" for band in bands]
            matched_granules = [gran for gran in granules if any(True for need in needed if need in gran)]
            if len(matched_granules) == len(bands):
                break

    for band in bands:
        granule = [gran for gran in matched_granules if f"_{band}" in gran][0]
        url = folder + granule + FILE_EXT
        download_file(url, f"{temp}/{band}{FILE_EXT}")
        subprocess.run(["ls", temp])

class SampleHolder:
    def __init__(self, bands):
        self.B01 = 0
        self.B02 = 0
        self.B03 = 0
        self.B04 = 0
        self.B05 = 0
        self.B06 = 0
        self.B07 = 0
        self.B07 = 0
        self.B08 = 0
        self.B09 = 0
        self.B8A = 0
        self.B09 = 0
        self.B11 = 0
        self.B12 = 0
        self.AOT = 0
        self.SCL = 0
        self.SNW = 0
        self.CLD = 0
        self.CLP = 0
        self.CLM = 0
        self.bands = bands
        self.count = len(bands)

    def update(self, vals):
        for i in range(self.count):
            self.__dict__[self.bands[i]] = vals[i]
    



class PixelProcessor:
    def __init__(self, pixelFn, bands):
        self.pixelFn = pixelFn
        self.bands = bands
        self.sample = SampleHolder(bands)

    def process(self, slice):
        self.sample.update(slice)
        return self.pixelFn(self.sample)

def _get_features(gdf):
    """Function to parse features from GeoDataFrame in such a manner that rasterio wants them"""
    import json
    return [json.loads(gdf.to_json())['features'][0]['geometry']]

def rerender(temp: str, req, setup, evalPx=None):
    points = req.input.bounds.bbox
    bbox = box(points[0], points[1], points[2], points[3])
    geo = gpd.GeoDataFrame({'geometry': bbox}, index=[0])
    dst_crs = 'EPSG:4326'
    geo.crs = dst_crs

    bands = setup["input"]
    srcs = [
        rasterio.open(temp + "/" + band + FILE_EXT, driver='JP2OpenJPEG')
        for band in bands
    ]
    count = setup["output"]["bands"]
    sampleType = setup['output'].get("sampleType", "AUTO")
    wanted_dtype = sample_type_to_dtype[sampleType]
    output_loc = temp + "/" + "output.tiff"

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
                print("reprojecting ", band)
                reproject(
                    source=rasterio.band(srcs[i], 1),
                    destination=dest,
                    src_transform=unproj.transform,
                    src_crs=unproj.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest)
                # convert band data to common format
                print("reformatting band")
                band_def = band_data_defs[req.input.data[0].type][band]
                dest = band_def["convert"](dest.astype(np.float32))
                dst.write(dest, i+1)
        with proj_bands.open() as src:
            data, transform = rasterio.mask.mask(src, shapes=_get_features(geo), all_touched=True, crop=True, filled=True)
            data = data.astype(np.float32)
            # do per-pixel preprocessing on masked data
            if evalPx:
                print("running evalscript")
                px = PixelProcessor(evalPx, bands)
                data = np.apply_along_axis(px.process, 0, data)
            # write output
            with rasterio.open(
                output_loc, 
                "w", 
                driver="Gtiff", 
                width=req.output.width, 
                height=req.output.height, 
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