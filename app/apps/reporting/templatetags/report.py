from django import template

from itertools import islice
from math import ceil

from collections import Counter

register = template.Library()

@register.filter
def split(value, char=None):
    return value.split(char)

def chunk_data(data):
    SIZE = ceil(len(data) / 12)
    it = iter(data)
    if data:
        for i in range(0, len(data), SIZE):
            yield {k:data[k] for k in islice(it, SIZE)}

@register.filter
def chunk_dict(data):
    raw_text = dict(sorted(Counter(data).items()))
    raw_text.pop(" ")
    raw_data = list(raw_text.items())
    val_dict = {str(i): {raw_data[i]} for i in range(len(raw_data))}
    return list(chunk_data(val_dict))

@register.filter
def count_items(value):
    return dict(Counter(value.split('|'))).items()