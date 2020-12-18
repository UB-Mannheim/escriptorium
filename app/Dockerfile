# pull official base image
FROM python:3.7.5-buster

# ARG KRAKEN_VERSION=3.0b5
# EXPOSE 8000

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# try to autodetect number of cpus available
# ENV NGINX_WORKER_PROCESSES auto

ARG VERSION_DATE="passthistobuildcmd"
ENV VERSION_DATE=$VERSION_DATE

# update apk
RUN apt-get update

RUN addgroup --system uwsgi
RUN adduser --system --no-create-home --ingroup uwsgi uwsgi

RUN apt-get install netcat-traditional jpegoptim pngcrush
RUN apt-get --assume-yes install libvips

COPY ./requirements.txt /usr/src/app/requirements.txt

# set work directory
WORKDIR /usr/src/app

RUN pip install --upgrade pip
RUN pip install -U -r requirements.txt

COPY ./entrypoint.sh /usr/src/app/entrypoint.sh
COPY . /usr/src/app/

# run entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
