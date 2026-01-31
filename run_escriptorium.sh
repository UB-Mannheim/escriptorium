#!/usr/bin/env bash

basedir=$(cd $(dirname $0) && pwd)
hostname=$(hostname)

# echo basedir=$basedir, hostname=$hostname, HOSTNAME=$HOSTNAME

export DJANGO_SETTINGS_MODULE=escriptorium.local_settings
export ESC_LANGUAGES="de,en,fr"
export LANG=C.UTF-8

if [ "$HOSTNAME" = "ocr-01" ]; then
  if [ "$basedir" != "/opt/es_next" ]; then
    # https://ocr-bw.bib.uni-mannheim.de/escriptorium

    source $basedir/../venv3.11/bin/activate
    export OMP_NUM_THREADS=2

    # Configuration for passim (alignment). Use 4 threads and 8 GiB RAM.
    # See https://github.com/dasmiq/passim and
    # https://spark.apache.org/docs/latest/configuration.html.
    export SPARK_SUBMIT_ARGS='--master local[4] --driver-memory 8G --executor-memory 8G'
    # The following setting has no effect (therefore disabled).
    #export SPARK_LAUNCHER_OPTS=-Xmx512m

    cd $basedir/app
    celery --app escriptorium worker --concurrency 16 --queues default --loglevel INFO --max-tasks-per-child=16 --optimization fair &
    # for everything that needs a java virtual machine (except search)
    celery --app escriptorium worker --concurrency 2 --queues jvm --loglevel INFO --optimization fair &
    # for everything that needs to be done on the spot to update the ui
    celery --app escriptorium worker --concurrency 2 --queues live --loglevel INFO --optimization fair &
    celery --app escriptorium worker --concurrency 4 --queues low-priority --loglevel INFO --optimization fair &
    # for everything that could use a GPU
    celery --app escriptorium worker --concurrency 2 --queues gpu --loglevel INFO --max-tasks-per-child=1 --optimization fair &
    python manage.py runserver --settings escriptorium.local_settings --verbosity 2 0.0.0.0:8080
    # celery worker -l INFO -E -A escriptorium --optimization fair --prefetch-multiplier 1 --queues default -c ${CELERY_MAIN_CONC:-10} --max-tasks-per-child=10

  else
    # https://ocr-bw.bib.uni-mannheim.de/es-next

    source $basedir/venv3.11/bin/activate
    export OMP_NUM_THREADS=1

    cd $basedir/app
    celery --app escriptorium worker --concurrency 4 --queues next-default --loglevel DEBUG &
    python -Wa manage.py runserver --settings escriptorium.local_settings --verbosity 3 0.0.0.0:8081

  fi

elif [ "$HOSTNAME" = "ocr-02" ]; then
  # https://ocr-bw.bib.uni-mannheim.de/escriptorium2

  source $basedir/../venv3.12/bin/activate
  export OMP_NUM_THREADS=1

  cd $basedir/app
  celery --app escriptorium worker --concurrency 16 --loglevel DEBUG &
  python -Wa manage.py runserver --settings escriptorium.local_settings --verbosity 3 0.0.0.0:8080

else

  echo "ERROR: Missing code for host $HOSTNAME!"
  exit 1

fi
