import json

from django import template


register = template.Library()

@register.filter
def values_list(obj, field):
    return list(obj.values_list(field, flat=True))