from django.conf import settings


def custom_homepage(request):
    return {'CUSTOM_HOME': getattr(settings, 'CUSTOM_HOME', False)}
