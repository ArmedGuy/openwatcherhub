FROM nvidia/cuda:12.8.0-cudnn-devel-ubuntu24.04

# get GDAL with tiff support
ENV ROOTDIR /usr/local/
ARG GDAL_VERSION=3.10.1
ARG OPENJPEG_VERSION=2.5.2

# Load assets
WORKDIR $ROOTDIR/

ARG DEBIAN_FRONTEND=noninteractive

# Install basic dependencies
RUN apt-get update -y && apt-get install -y \
    software-properties-common \
    build-essential \
    python3-pip \
    python3-numpy \
    libspatialite-dev \
    sqlite3 \
    libpq-dev \
    libcurl4-gnutls-dev \
    libcrypto++-dev \
    libproj-dev \
    libxml2-dev \
    libgeos-dev \
    libnetcdf-dev \
    libpoppler-dev \
    libspatialite-dev \
    libhdf4-alt-dev \
    libhdf5-serial-dev \
    bash-completion \
    cmake \
    curl

ADD http://download.osgeo.org/gdal/${GDAL_VERSION}/gdal-${GDAL_VERSION}.tar.gz $ROOTDIR/src/
ADD https://github.com/uclouvain/openjpeg/archive/v${OPENJPEG_VERSION}.tar.gz $ROOTDIR/src/openjpeg-${OPENJPEG_VERSION}.tar.gz

# Compile and install OpenJPEG
RUN cd src && tar -xvf openjpeg-${OPENJPEG_VERSION}.tar.gz && cd openjpeg-${OPENJPEG_VERSION}/ \
    && mkdir build && cd build \
    && cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$ROOTDIR \
    && make -j $(nproc) && make install && make clean \
    && cd $ROOTDIR && rm -Rf src/openjpeg*

# Compile and install GDAL
RUN cd src && tar -xvf gdal-${GDAL_VERSION}.tar.gz && cd gdal-${GDAL_VERSION} \
    && mkdir build && cd build && cmake .. -DGGDAL_USE_OPENCL=YES -DUSE_OPENCL=YES && cmake --build . -j $(nproc) && cmake --build . --target install \
    && apt-get update -y \
    && apt-get remove -y --purge build-essential python3-numpy

RUN echo $(find / -name gdal-config)


COPY ./requirements.txt /code/requirements.txt
#RUN python3 -m pip install -U pip --break-system-packages
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt --break-system-packages
RUN GDAL_CONFIG=/usr/local/bin/gdal-config pip install --no-binary rasterio rasterio --break-system-packages
COPY ./ /code/app
WORKDIR /code/app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]