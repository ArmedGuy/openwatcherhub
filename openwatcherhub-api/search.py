import typing
import requests

from models import ProcessRequest
from process import ProcessContext

BASE_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter="

mosaicking_order_to_orderby = {
    "mostRecent": "ContentDate/Start desc",
    "leastRecent": "ContentDate/Start asc",
    "leastCC": "ContentDate/Start desc"
}

def _maxCloudCover(val: float) -> typing.List[str]:
    return [f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value le {val})"]

def _bbox(corners: typing.List[float]) -> typing.List[str]:
    lower = (corners[0], corners[1])
    higher = (corners[2], corners[3])
    points = [
        lower,
        (lower[0], higher[1]),
        higher,
        (higher[0], lower[1]),
        lower
    ]
    poly = f"POLYGON(({','.join(str(point[0]) + ' ' + str(point[1]) for point in points)}))"
    return [f"OData.CSC.Intersects(area=geography'SRID=4326;{poly}')"]

def _between(start_date: str, end_date: str) -> typing.List[str]:
    return [
        f"ContentDate/Start gt {start_date}",
        f"ContentDate/Start lt {end_date}",
    ]

def search(ctx: ProcessContext):
    baseFilters = _bbox(ctx.request.input.bounds.bbox)

    for data in ctx.request.input.data:
        filters =  ctx.product["odata"]["searchTerms"] + baseFilters
        filters += _between(data.dataFilter.timeRange.from_, data.dataFilter.timeRange.to)
        filters += _maxCloudCover(data.dataFilter.maxCloudCoverage)

        filter_str = ' and '.join(filters)

        orderby = mosaicking_order_to_orderby[data.dataFilter.mosaickingOrder]

        req_url = BASE_URL + filter_str + "&$orderby=" + orderby + "&$expand=Attributes"
        print(req_url)
        res = requests.get(req_url)

        ret = res.json()['value']
        if data.dataFilter.mosaickingOrder == "leastCC":
            # sort by cloud coverage
            print("resort the array")
            ret = sorted(ret, key=lambda key: [attr['Value'] for attr in key["Attributes"] if attr["Name"] == "cloudCover"][0])
        return ret

