#!/bin/bash

source /home/stweil/src/gitlab/scripta/escriptorium/venv/bin/activate
export DJANGO_SETTINGS_MODULE=escriptorium.local_settings
export ESC_LANGUAGES="de,en,fr"

cd /home/stweil/src/gitlab/scripta/escriptorium/app
celery worker --app escriptorium --concurrency 2 --loglevel DEBUG &
python -Wa manage.py runserver --settings escriptorium.local_settings --verbosity 3 0.0.0.0:8080
