from django import template

from itertools import islice
from math import ceil

from collections import Counter, OrderedDict
from django.db.models import Sum
from django.contrib.postgres.aggregates.general import StringAgg

register = template.Library()

def chunk_data(data):
    SIZE = ceil(len(data) / 12)
    it = iter(data)
    if data:
        for i in range(0, len(data), SIZE):
            yield {k:data[k] for k in islice(it, SIZE)}

def get_aggregate(model, field, delimiter=' '):
    return model.aggregate(data=StringAgg(field, delimiter=delimiter)).get('data')

@register.filter
def aggregate_value(model, field):
    return get_aggregate(model, field)

@register.filter
def chunk_dict(data):
    raw_text = dict(sorted(Counter(data).items()))
    if data:
        raw_text.pop(" ")
    raw_data = list(raw_text.items())
    val_dict = {str(i): {raw_data[i]} for i in range(len(raw_data))}
    return list(chunk_data(val_dict))

@register.filter
def get_count(model, field):
    value = model.aggregate(Sum(field)).get(field + '__sum')
    return 0 if value is None else value

@register.filter
def get_typology_count(model, field):
    value = get_aggregate(model, field, '|')
    return OrderedDict(Counter(value.split('|')).most_common()).items() if value else ''