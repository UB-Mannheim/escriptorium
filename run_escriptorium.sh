#!/bin/bash

source /home/stweil/src/gitlab/scripta/venv3.11/bin/activate
export DJANGO_SETTINGS_MODULE=escriptorium.local_settings
export ESC_LANGUAGES="de,en,fr"

export OMP_NUM_THREADS=1

cd /home/stweil/src/gitlab/scripta/escriptorium/app
celery --app escriptorium worker --concurrency 16 --loglevel DEBUG &
python -Wa manage.py runserver --settings escriptorium.local_settings --verbosity 3 0.0.0.0:8080
