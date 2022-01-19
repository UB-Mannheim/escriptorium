import os.path
import celery.app.trace

from celery import signals

from reporting.tasks import create_task_reporting

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
REDIS_DB = 1

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA_ROOT = os.path.join(BASE_DIR, 'test_media')

class DisableMigrations(object):

        def __contains__(self, item):
            return True

        def __getitem__(self, item):
            return None

MIGRATION_MODULES = DisableMigrations()

KRAKEN_TRAINING_LOAD_THREADS = 0

# Disables easy-thumbnail spamming
THUMBNAIL_OPTIMIZE_COMMAND = {}

# Trigger before_task_publish signal even using celery eager mode
old_build_tracer = celery.app.trace.build_tracer


def build_tracer_patched(name, task, *args, **kwargs):
    before_task_publish_receivers = signals.before_task_publish.receivers
    old_trace_task = old_build_tracer(name, task, *args, **kwargs)

    def trace_task_patched(uuid, args, kwargs, request=None):
        if before_task_publish_receivers:
            create_task_reporting(sender=task, body=(args, kwargs), headers={"id": uuid})
        return old_trace_task(uuid, args, kwargs, request)

    return trace_task_patched


celery.app.trace.build_tracer = build_tracer_patched
