# Local settings for eScriptorium on ocr-bw

from escriptorium.settings import *

DOMAIN = 'ocr-bw.bib.uni-mannheim.de'
CSRF_TRUSTED_ORIGINS = ['ocr-bw.bib.uni-mannheim.de']

# In the format [('Full Name', 'email@example.com'), ('Full Name', 'anotheremail@example.com')]
ADMINS = [
        ('Administrator', 'stefan.weil@bib.uni-mannheim.de'),
]
ADMINS = ['Administrator <stefan.weil@bib.uni-mannheim.de>']

# Run in subpath
#BASE_URL = 'https://ocr-bw.bib.uni-mannheim.de/escriptorium/'

# Settings for running from a subpath.
##FORCE_SCRIPT_NAME = '/escriptorium'
##STATIC_URL = '/escriptorium/static/'

#LOGIN_REDIRECT_URL = '/escriptorium/projects/'
#LOGOUT_REDIRECT_URL = FORCE_SCRIPT_PATH + '/'
#STATIC_URL = '/xxx/static/'
#STATIC_URL = '/static/'
#SCRIPT_PATH = '/escriptorium'

#ALLOWED_HOSTS = ['localhost', 'ub-blade-10.bib.uni-mannheim.de', '134.155.36.10']
DEFAULT_FROM_EMAIL = 'noreply@bib.uni-mannheim.de'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'localhost'
TIME_ZONE = 'Europe/Berlin'
USE_TZ = False
VERSION_DATE = 'develop (2022-01-30)'

LOCALE_PATHS = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "locale"),
]

DEBUG=True

# https://stackoverflow.com/questions/62047354/build-absolute-uri-with-https-behind-reverse-proxy
#USE_X_FORWARDED_HOST = True

DATABASES = {
    'default': {
        'ENGINE': os.getenv('SQL_ENGINE', 'django.db.backends.postgresql'),
        'NAME': os.getenv('SQL_DATABASE', 'escriptorium'),

        # Needed for some configuration
        # 'USER': os.getenv('POSTGRES_USER', 'provideyourusernamehere'),
        # 'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'provideyourpasswordhere'),
    }
}

INSTALLED_APPS += ['debug_toolbar', 'django_extensions']
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware',]
INTERNAL_IPS = ['127.0.0.1',]

# only needed in development
# EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = '/tmp/django-emails'

# KRAKEN_TRAINING_DEVICE = 'cuda:0'

DEBUG_TOOLBAR_CONFIG = {
   'SHOW_TOOLBAR_CALLBACK': lambda r: False,  # disables it
}

DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
#   'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
]

USE_CELERY = True
# CELERY_TASK_ALWAYS_EAGER = True

# LOGGING['loggers']['kraken']['level'] = 'DEBUG'

CUSTOM_HOME = True
