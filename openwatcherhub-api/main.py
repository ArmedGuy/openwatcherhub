from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

import tempfile
import json

from models import ProcessRequest
from search import search
from evalscript import compile

from process import format_setup, download, rerender, ProcessContext

from products import SUPPORTED_PRODUCTS

app = FastAPI()



@app.post("/api/v1/process")
async def process(req: ProcessRequest):
    ctx = ProcessContext(req)

    product_type = req.input.data[0].type
    if product_type not in SUPPORTED_PRODUCTS:
        raise HTTPException(status_code=422, detail=f"{product_type} is not supported.")
    
    ctx.product = SUPPORTED_PRODUCTS[product_type]

    script = compile(req.evalscript)
    
    # get important setup params
    setup = script["setup"]()
    ctx.setup = format_setup(setup)
    
    res = search(ctx)
    #print(json.dumps(res, indent=2))

    best = res[0]
    for r in res:
        print("cloud cover", [attr['Value'] for attr in r["Attributes"] if attr["Name"] == "cloudCover"][0])
    ctx.temp_dir = tempfile.mkdtemp()
    ctx.evaluatePixelFunction = script.get("evaluatePixel", None)
    # download the current band
    download(ctx, best)

    rerender(ctx)
    return FileResponse(ctx.temp_dir + "/" + "output.tiff")
