import os.path

CELERY_TASK_ALWAYS_EAGER = True
REDIS_DB = 1

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA_ROOT = os.path.join(BASE_DIR, 'test_media')

class DisableMigrations(object):

        def __contains__(self, item):
            return True

        def __getitem__(self, item):
            return None

MIGRATION_MODULES = DisableMigrations()

# Disables easy-thumbnail spamming
THUMBNAIL_OPTIMIZE_COMMAND = {}
