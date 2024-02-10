SENTINEL_2_1C = "sentinel-2-l1c"
SENTINEL_2_2A = "sentinel-2-l2a"

import numpy as np

class SampleHolder:
    def __init__(self, bands):
        self.bands = bands
        self.count = len(bands)

    def update(self, vals):
        for i in range(self.count):
            self.__dict__[self.bands[i]] = vals[i]


# Sentinel 2 2A product

optical_band = {
    "src": np.uint16,
    "defaultUnit": "REFLECTANCE",
    "units": {
        "REFLECTANCE": {
            "convert": lambda x: ((x - 1000) / 10000)
        },
        "DN": {
            "convert": lambda x: x
        }
    }
}

dn_band = {
    "src": np.uint8,
    "defaultUnit": "DN",
    "units": {
        "DN": {
            "convert": lambda x: x
        }
    }
}

sentinel_2_2a_resolutions = ["10m", "20m", "60m"]
def sentinel_2_2a_matching(bands, granules):
    for res in sentinel_2_2a_resolutions:
        needed = [f"{band}_{res}" for band in bands]
        matched_granules = [gran for gran in granules if any(True for need in needed if need in gran)]
        if len(matched_granules) == len(bands):
            return matched_granules
    return []
        
class S2L2ASampleHolder(SampleHolder):
    def __init__(self, bands):
        super().__init__(bands)
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


SUPPORTED_PRODUCTS = {
    SENTINEL_2_2A: {
        "odata": {
            "searchTerms": ["Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'S2MSI2A')"]
        },
        "granules": {
            "granuleFile": "MTD_MSIL2A.xml",
            "matching": sentinel_2_2a_matching
        },
        "bands": {
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
        },
        "sampleHolder": S2L2ASampleHolder
    }
}