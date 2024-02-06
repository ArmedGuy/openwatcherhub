# openwatcherhub
This is a proof of concept for a locally hosted version of the featureset SentinelHub has, the product that is being pushed as the easiest way to work with Sentinel data.

The project attempts to reimplement certain interfaces of SentinelHub's APIs, and provide a somewhat equivalent feature-set.

The project currently has two main components:
 - copernicus-dataspace-s3-cache
 - openwatcherhub-api


# copernicus-dataspace-s3-cache
A modified nginx-s3-gateway docker image configured to download and cache Sentinel satellite bands from the Copernicus S3 repository.
The local caching helps keep the bandwidth usage down, and enables fast reprocessing of the same bands.

# openwatcherhub-api
This is currently an all-in-one API service that can respond to certain SentinelHub requests.
It is designed without ANY kind of security, and is only suitable for local installations.

It is also terribly inefficient. It will be rewritten for maturity and only then will performance be taken into account.

### Currently supported
 - /api/v1/process endpoint
 - basic evalscript, only older ecmascript support (no arrow functions etc)
 - single input, band selection
 - single output to tiff only
 - only nearest resampling
 - only sentinel2-l2a products, will add 1 later
 - no mosaicking, just order by cloud coverage and pray

evalscript is implemented by transpiling JavaScript to Python (partially) and executing it through python exec

### Running this locally
docker compose is the easiest way for now. Make sure to change (and NOT commit) the s3 access key and secret.

### Pointing SentinelHub code to this instance
Start by pointing the SHConfig base url to the instance:

```python
config = SHConfig()
config.sh_client_id = "DENADA"
config.sh_client_secret = "NOTHING"
config.sh_token_url = ""
config.sh_base_url = "http://127.0.0.1:8081"
```

Then set the URL for the specific data collection for a request:
```python
request_true_color = SentinelHubRequest(
    evalscript=evalscript_true_color,
    input_data=[
        SentinelHubRequest.input_data(
            data_collection=DataCollection.SENTINEL2_L2A.define_from(
                name="s2", service_url="http://127.0.0.1:8081"
            ),
            time_interval=("2023-07-01", "2023-07-20"),
            other_args={"dataFilter": {"mosaickingOrder": "leastCC"}},
        )
    ],
    responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
    bbox=aoi_bbox,
    size=aoi_size,
    config=config,
)
```

Because this system doesn't use OAuth2 at all, you must trick SentinelHub python library to work without it.

Add this snippet somewhere at the top of your file/notebook, which patches the SentinelHubSession to not attempt to fetch an auth token.

```python
from sentinelhub.download.session import SentinelHubSession
SentinelHubSession._collect_new_token = lambda self: {'access_token': "herpderp", "expires_at": 0}
```

Full example available in `openwatcherhub_test.ipynb`.