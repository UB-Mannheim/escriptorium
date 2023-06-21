#!/bin/bash

source /home/stweil/src/gitlab/scripta/escriptorium/venv3.9/bin/activate
export DJANGO_SETTINGS_MODULE=escriptorium.local_settings
export ESC_LANGUAGES="de,en,fr"
export LANG=C.UTF-8
export OMP_NUM_THREADS=4

# Configuration for passim (alignment). Use 4 threads and 8 GiB RAM.
# See https://github.com/dasmiq/passim and
# https://spark.apache.org/docs/latest/configuration.html.
export SPARK_SUBMIT_ARGS='--master local[4] --driver-memory 8G --executor-memory 8G'
# The following setting has no effect (therefore disabled).
#export SPARK_LAUNCHER_OPTS=-Xmx512m

celery worker --app escriptorium --concurrency 8 --loglevel INFO &
python manage.py runserver --settings escriptorium.local_settings --verbosity 2 0.0.0.0:8080
