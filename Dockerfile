FROM node:12-alpine as frontend

WORKDIR /build
COPY ./front /build
RUN npm ci && npm run production

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
ENV FRONTEND_DIR=/usr/src/app/front

# update apk
RUN apt-get update

RUN addgroup --system uwsgi
RUN adduser --system --no-create-home --ingroup uwsgi uwsgi

RUN apt-get install netcat-traditional jpegoptim pngcrush
RUN apt-get --assume-yes install libvips

# set work directory
WORKDIR /usr/src/app

RUN pip install --upgrade pip

COPY ./app/requirements.txt /usr/src/app/requirements.txt
RUN pip install -U -r requirements.txt

COPY ./app/entrypoint.sh /usr/src/app/entrypoint.sh
COPY ./app /usr/src/app/
COPY --from=frontend /build/dist /usr/src/app/front

# run entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
