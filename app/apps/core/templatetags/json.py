import json

from django import template

register = template.Library()


@register.filter
def jsond(obj):
    return json.dumps(obj)
