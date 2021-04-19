from django.conf import settings


def enable_cookie_consent(request):
    return {'ENABLE_COOKIE_CONSENT': getattr(settings,
                                             'ENABLE_COOKIE_CONSENT',
                                             True)}

def custom_homepage(request):
    return {'CUSTOM_HOME': getattr(settings, 'CUSTOM_HOME', False)}
