# openwatcherhub
This is a proof of concept for a locally hosted version of SentinelHub, the product that is being pushed as the easiest way to work with Sentinel data.

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