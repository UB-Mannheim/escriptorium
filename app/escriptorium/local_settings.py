# Local settings for eScriptorium on ocr-bw

import os

from escriptorium.settings import INSTALLED_APPS, MIDDLEWARE

DOMAIN = 'ocr-bw.bib.uni-mannheim.de'
CSRF_TRUSTED_ORIGINS = ['ocr-bw.bib.uni-mannheim.de']

# In the format [('Full Name', 'email@example.com'), ('Full Name', 'anotheremail@example.com')]
ADMINS = [
    ('Administrator', 'stefan.weil@uni-mannheim.de')
]
# ADMINS = ['Administrator <stefan.weil@uni-mannheim.de>']

# Settings for running from a subpath.
FORCE_SCRIPT_NAME = '/escriptorium2'
# Relative MEDIA_URL requires at least Django 4.0.
MEDIA_URL = 'https://ocr-bw.bib.uni-mannheim.de' + FORCE_SCRIPT_NAME + '/media/'
# Relative STATIC_URL requires at least Django 4.0.
STATIC_URL = FORCE_SCRIPT_NAME + '/static/'
LOGIN_REDIRECT_URL = FORCE_SCRIPT_NAME + '/projects/'
LOGOUT_REDIRECT_URL = FORCE_SCRIPT_NAME + '/'
USE_X_FORWARDED_HOST = True

# ALLOWED_HOSTS = ['localhost', 'ub-blade-10.bib.uni-mannheim.de', '134.155.36.10']
DEFAULT_FROM_EMAIL = 'stefan.weil@uni-mannheim.de'

# Sender e-mail address for log messages sent by e-mail.
SERVER_EMAIL = 'stefan.weil@uni-mannheim.de'

# https://docs.djangoproject.com/en/3.2/topics/email/
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'localhost'
# EMAIL_HOST = 'smtp.mail.uni-mannheim.de'
# EMAIL_HOST_USER = 'xxx'
# EMAIL_HOST_PASSWORD = 'xxx'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# SMTP_DOMAIN=uni-mannheim.de

TIME_ZONE = 'Europe/Berlin'
USE_TZ = True
VERSION_DATE = 'develop (2022-03-12)'

LOCALE_PATHS = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "locale"),
]

DEBUG = True

# https://stackoverflow.com/questions/62047354/build-absolute-uri-with-https-behind-reverse-proxy
# USE_X_FORWARDED_HOST = True

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
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
INTERNAL_IPS = ['127.0.0.1']

# only needed in development
# EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = '/tmp/django-emails'

KRAKEN_TRAINING_DEVICE = 'cuda:0'

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
    # 'debug_toolbar.panels.staticfiles.StaticFilesPanel',
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
