# pull official base image
FROM python:3.6-stretch

# EXPOSE 8000

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# try to autodetect number of cpus available
# ENV NGINX_WORKER_PROCESSES auto

# set work directory
WORKDIR /usr/src/app

# update apk
RUN apt-get update

RUN addgroup --system uwsgi
RUN adduser --system --no-create-home --ingroup uwsgi uwsgi

RUN apt-get install netcat-traditional pngcrush

RUN pip install --upgrade pip

COPY ./requirements.txt /usr/src/app/requirements.txt
RUN pip install -U -r requirements.txt

COPY ./sendmail_config.sh "/usr/src/app/sendmail_config.sh"
RUN ./sendmail_config.sh

COPY ./entrypoint.sh /usr/src/app/entrypoint.sh
COPY . /usr/src/app/

# run entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
