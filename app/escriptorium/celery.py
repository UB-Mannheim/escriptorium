from __future__ import absolute_import, unicode_literals

import os

from celery import Celery, signals
from celery.app import trace

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'escriptorium.settings')

app = Celery('escriptorium')

# Using a string here means the worker doesn't have to serialize
# the configuration object to the child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@signals.celeryd_init.connect
def _use_spawn_pool(**kwargs):
    # forked children crash (SIGSEGV in CoreFoundation) once the worker has
    # loaded native libraries (torch, pyvips, ...); spawn re-execs a clean
    # interpreter for each pool child instead.
    from billiard import set_start_method
    set_start_method('spawn')


@signals.worker_process_init.connect
def _reinit_worker_optimizations(**kwargs):
    # Celery 5.6 only populates the process-local trace._localized in pool
    # children when FORKED_BY_MULTIPROCESSING is set, which billiard never
    # does; without this, the first task in a spawned child fails with
    # "not enough values to unpack (expected 3, got 0)".
    from celery import current_app
    trace.setup_worker_optimizations(current_app)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
