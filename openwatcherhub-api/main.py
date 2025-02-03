from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import asyncio

import os
#os.environ["PROJ_DEBUG"] = "2"

import logging

console_handler = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s:%(message)s")
console_handler.setFormatter(formatter)
logger = logging.getLogger("rasterio")
logger.addHandler(console_handler)
#logger.setLevel(logging.DEBUG)

import tempfile
import json

from models import ProcessRequest
from search import search
from evalscript import compile

from process import format_setup, download, render, ProcessContext

from products import SUPPORTED_PRODUCTS

app = FastAPI()



@app.post("/api/v1/process")
async def process(req: ProcessRequest):
    ctx = ProcessContext(req)

    product_type = req.input.data[0].type
    if product_type not in SUPPORTED_PRODUCTS:
        raise HTTPException(status_code=422, detail=f"{product_type} is not supported.")
    
    ctx.product = SUPPORTED_PRODUCTS[product_type]

    vectorized_evalscript = False
    if "VECTORIZE" in req.evalscript:
        vectorized_evalscript = True
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
    # download the bands for all of these
    await download(ctx, best)

    await render(ctx, vectorized_evalscript)
    #rerender(ctx)
    return FileResponse(ctx.temp_dir + "/" + "output.tiff")
