SENTINEL_2_1C = "sentinel-2-l1c"
SENTINEL_2_2A = "sentinel-2-l2a"

import numpy as np

class SampleHolder:
    def __init__(self, bands, vectorize=False):
        self.bands = bands
        self.count = len(bands)
        self.vectorize = vectorize

    def update(self, vals):
        for i in range(self.count):
            if self.vectorize:
                self.__dict__[self.bands[i]] = vals[i, :, :]
            else:
                self.__dict__[self.bands[i]] = vals[i]

# Sentinel 2 1C product
            
s1c_optical_band = {
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

def sentinel_2_1c_matching(bands, granules):
    needed = [f"_{band}" for band in bands]
    matched_granules = [gran for gran in granules if any(True for need in needed if need in gran)]
    if len(matched_granules) == len(bands):
        return matched_granules
    return []

class S2L1CSampleHolder(SampleHolder):
    def __init__(self, bands, vectorize):
        super().__init__(bands, vectorize)
        """self.B01 = 0
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
        self.CLP = 0
        self.CLM = 0"""

# Sentinel 2 2A product

s2a_optical_band = {
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
    def __init__(self, bands, vectorize):
        super().__init__(bands, vectorize)
        """self.B01 = 0
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
        self.CLM = 0"""


SUPPORTED_PRODUCTS = {
    SENTINEL_2_1C: {
        "odata": {
            "searchTerms": ["Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'S2MSI1C')"]
        },
        "granules": {
            "granuleFile": "MTD_MSIL1C.xml",
            "matching": sentinel_2_1c_matching
        },
        "bands": {
            "B01": s1c_optical_band,
            "B02": s1c_optical_band,
            "B03": s1c_optical_band,
            "B04": s1c_optical_band,
            "B05": s1c_optical_band,
            "B06": s1c_optical_band,
            "B07": s1c_optical_band,
            "B07": s1c_optical_band,
            "B08": s1c_optical_band,
            "B09": s1c_optical_band,
            "B8A": s1c_optical_band,
            "B09": s1c_optical_band,
            "B11": s1c_optical_band,
            "B12": s1c_optical_band,
            "CLP": dn_band,
            "CLM": dn_band
        },
        "sampleHolder": S2L1CSampleHolder
    },
    SENTINEL_2_2A: {
        "odata": {
            "searchTerms": ["Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq 'S2MSI2A')"]
        },
        "granules": {
            "granuleFile": "MTD_MSIL2A.xml",
            "matching": sentinel_2_2a_matching
        },
        "bands": {
            "B01": s2a_optical_band,
            "B02": s2a_optical_band,
            "B03": s2a_optical_band,
            "B04": s2a_optical_band,
            "B05": s2a_optical_band,
            "B06": s2a_optical_band,
            "B07": s2a_optical_band,
            "B07": s2a_optical_band,
            "B08": s2a_optical_band,
            "B09": s2a_optical_band,
            "B8A": s2a_optical_band,
            "B09": s2a_optical_band,
            "B11": s2a_optical_band,
            "B12": s2a_optical_band,
            "AOT": s2a_optical_band,
            "SCL": dn_band,
            "SNW": dn_band,
            "CLD": dn_band,
            "CLP": dn_band,
            "CLM": dn_band
        },
        "sampleHolder": S2L2ASampleHolder
    }
}
