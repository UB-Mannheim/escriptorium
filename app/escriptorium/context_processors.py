from django.conf import settings


def disable_search(request):
    return {'DISABLE_ELASTICSEARCH': getattr(settings,
                                             'DISABLE_ELASTICSEARCH',
                                             True)}


def enable_cookie_consent(request):
    return {'ENABLE_COOKIE_CONSENT': getattr(settings,
                                             'ENABLE_COOKIE_CONSENT',
                                             True)}


def custom_homepage(request):
    return {'CUSTOM_HOME': getattr(settings, 'CUSTOM_HOME', False)}


def enable_text_alignment(request):
    return {'TEXT_ALIGNMENT_ENABLED': getattr(settings,
                                              'TEXT_ALIGNMENT_ENABLED',
                                              True)}


def enable_markdown_export(request):
    return {'EXPORT_OPENITI_MARKDOWN_ENABLED': getattr(
        settings, 'EXPORT_OPENITI_MARKDOWN_ENABLED', True,
    )}


def enable_tei_export(request):
    return {'EXPORT_TEI_XML_ENABLED': getattr(settings,
                                              'EXPORT_TEI_XML_ENABLED',
                                              True)}
