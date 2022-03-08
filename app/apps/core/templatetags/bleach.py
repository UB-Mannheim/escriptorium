import bleach
from django import template

register = template.Library()


@register.filter
def strip_html(obj, tags=None):
    tags = tags or None
    return bleach.clean(obj, strip=True, tags=tags)
