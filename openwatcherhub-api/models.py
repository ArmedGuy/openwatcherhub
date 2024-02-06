from pydantic import BaseModel, Field
import typing

class ProcessRequestInputBounds(BaseModel):
    bbox: typing.List[float]

class TimeRange(BaseModel):
    from_: str = Field(..., alias='from')
    to: str

class GenericDataFilter(BaseModel):
    timeRange: TimeRange
    mosaickingOrder: str = "mostRecent"
    maxCloudCoverage: float = 100
    previewMode: str = "DETAIL"

class GenericProcessing(BaseModel):
    upsampling: str = "NEAREST"
    downsampling: str = "NEAREST"
    harmonizeValues: bool = True

class ProcessRequestInputData(BaseModel):
    type: str
    id: str = ""
    dataFilter: GenericDataFilter
    processing: GenericProcessing = None

class ProcessRequestInput(BaseModel):
    bounds: ProcessRequestInputBounds
    data: typing.List[ProcessRequestInputData]

class FormatType(BaseModel):
    type: str
    quality: int = 90

class ProcessRequestOutputResponse(BaseModel):
    identifier: str = "default"
    format: FormatType

class ProcessRequestOutput(BaseModel):
    width: int = 0
    height: int = 0
    resx: float = 0
    resy: float = 0
    responses: typing.List[ProcessRequestOutputResponse]

class ProcessRequest(BaseModel):
    input: ProcessRequestInput
    output: ProcessRequestOutput = None
    evalscript: str