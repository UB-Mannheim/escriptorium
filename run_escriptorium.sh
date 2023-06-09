#!/bin/bash

source /home/stweil/src/gitlab/scripta/escriptorium/venv3.9/bin/activate
export DJANGO_SETTINGS_MODULE=escriptorium.local_settings
export ESC_LANGUAGES="de,en,fr"
export LANG=C.UTF-8
export OMP_NUM_THREADS=4

celery worker --app escriptorium --concurrency 8 --loglevel INFO &
python manage.py runserver --settings escriptorium.local_settings --verbosity 2 0.0.0.0:8080
