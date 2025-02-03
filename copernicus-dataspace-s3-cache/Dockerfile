FROM nginxinc/nginx-s3-gateway:latest-20250120

ENV S3_SERVER_PROTO "https"
ENV S3_SERVER "eodata.dataspace.copernicus.eu"
ENV S3_BUCKET_NAME "eodata"
ENV S3_REGION "default"
ENV S3_SERVER_PORT "443"
ENV S3_STYLE "virtual-v2"
ENV AWS_SIGS_VERSION "4"

ENV PROXY_CACHE_MAX_SIZE "100g"
ENV PROXY_CACHE_INACTIVE "2d"
ENV PROXY_CACHE_VALID_OK "2d"
ENV PROXY_CACHE_VALID_NOTFOUND "1s"
ENV PROXY_CACHE_VALID_FORBIDDEN "1s"
ENV ALLOW_DIRECTORY_LIST "true"
ENV CORS_ENABLED 0

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
COPY default.conf.template /etc/nginx/templates/default.conf.template
