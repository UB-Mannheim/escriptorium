from django.conf import settings


def disable_search(request):
    return {'DISABLE_ELASTICSEARCH': getattr(settings,
                                             'DISABLE_ELASTICSEARCH',
                                             True)}


def enable_cookie_consent(request):
    return {'ENABLE_COOKIE_CONSENT': getattr(settings,
                                             'ENABLE_COOKIE_CONSENT',
                                             True)}


def languages(request):
    return {'ESC_LANGUAGES': getattr(settings, 'ESC_LANGUAGES', 'en').split(',')}


def custom_homepage(request):
    return {'CUSTOM_HOME': getattr(settings, 'CUSTOM_HOME', False)}
