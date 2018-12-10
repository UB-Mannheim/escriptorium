# pull official base image
FROM python:3.7-alpine

# EXPOSE 8000

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# try to autodetect number of cpus available
# ENV NGINX_WORKER_PROCESSES auto

# set work directory
WORKDIR /usr/src/app

# update apk
RUN apk update

# install uwsgi dependencies
# RUN apk add uwsgi-python3
RUN apk add gcc \
		    libc-dev \
		    linux-headers 

# install git (to install kraken from sources)
RUN apk add git

# install Pillow dependencies
RUN apk add jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev

RUN addgroup -S uwsgi && adduser -S -g uwsgi uwsgi

# install psycopg2
RUN apk add --virtual build-deps gcc python3-dev musl-dev \
    && apk add postgresql-dev \
    && pip install psycopg2 \
    && apk del build-deps

# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN pip install -r requirements.txt

# copy entrypoint.sh
COPY ./entrypoint.sh /usr/src/app/entrypoint.sh

# copy project
COPY . /usr/src/app/

# run entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
