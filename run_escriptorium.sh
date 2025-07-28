#!/bin/bash

source /home/stweil/src/gitlab/scripta/venv3.11/bin/activate
export DJANGO_SETTINGS_MODULE=escriptorium.local_settings
export ESC_LANGUAGES="de,en,es,fr"
export LANG=C.UTF-8
export OMP_NUM_THREADS=2

# Configuration for passim (alignment). Use 4 threads and 8 GiB RAM.
# See https://github.com/dasmiq/passim and
# https://spark.apache.org/docs/latest/configuration.html.
export SPARK_SUBMIT_ARGS='--master local[4] --driver-memory 8G --executor-memory 8G'
# The following setting has no effect (therefore disabled).
#export SPARK_LAUNCHER_OPTS=-Xmx512m

celery --app escriptorium worker --concurrency 16 --queues default --loglevel INFO --max-tasks-per-child=16 --optimization fair &
# for everything that needs a java virtual machine (except elasticsearch)
celery --app escriptorium worker --concurrency 2 --queues jvm --loglevel INFO --optimization fair &
# for everything that needs to be done on the spot to update the ui
celery --app escriptorium worker --concurrency 2 --queues live --loglevel INFO --optimization fair &
celery --app escriptorium worker --concurrency 4 --queues low-priority --loglevel INFO --optimization fair &
# for everything that could use a GPU
celery --app escriptorium worker --concurrency 2 --queues gpu --loglevel INFO --max-tasks-per-child=1 --optimization fair &
python manage.py runserver --settings escriptorium.local_settings --verbosity 2 0.0.0.0:8080
# celery worker -l INFO -E -A escriptorium --optimization fair --prefetch-multiplier 1 --queues default -c ${CELERY_MAIN_CONC:-10} --max-tasks-per-child=10
