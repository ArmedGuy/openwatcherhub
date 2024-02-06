from fastapi import FastAPI
from fastapi.responses import FileResponse

import tempfile
import json

from models import ProcessRequest
from search import search
from evalscript import compile

from process import download, rerender

app = FastAPI()



@app.post("/api/v1/process")
async def process(req: ProcessRequest):
    print(req)
    script = compile(req.evalscript)
    
    # get important setup params
    setup = script["setup"]()
    bands = setup["input"]
    
    res = search(req)
    #print(json.dumps(res, indent=2))

    test = res[0]
    for r in res:
        print("cloud cover", [attr['Value'] for attr in r["Attributes"] if attr["Name"] == "cloudCover"][0])
    tmp = tempfile.mkdtemp()
    print(tmp)
    #bands = ["B04", "B03", "B02"]
    download(tmp, test["S3Path"], req.input.data[0].type, bands)
    rerender(
        tmp, 
        req,
        setup,
        evalPx=script.get("evaluatePixel", None)
    )
    return FileResponse(tmp + "/" + "output.tiff")
