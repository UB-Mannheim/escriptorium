FROM python:3.7.5-slim

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND=non-interactive

# set work directory
WORKDIR /usr/src/app

# Install base Debian packages
# and cleanup afterwards to reduce image size
RUN apt-get update -q && \
    apt-get -y -qq install --no-install-recommends netcat-traditional jpegoptim \
    pngcrush libvips libffi-dev git build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Add non privileged user to run the app
RUN addgroup --system uwsgi
RUN adduser --system --no-create-home --ingroup uwsgi uwsgi

RUN pip install -q --upgrade pip

# Install Python packages and remove cache
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN pip --no-cache-dir install -q -r requirements.txt
