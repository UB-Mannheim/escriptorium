from collections import Counter
from itertools import islice
from math import ceil

from django import template

register = template.Library()


def chunk_data(data):
    SIZE = ceil(len(data) / 12)
    it = iter(data)
    if data:
        for i in range(0, len(data), SIZE):
            yield {k: data[k] for k in islice(it, SIZE)}


@register.filter
def chunk_dict(data):
    raw_text = dict(sorted(Counter(data).items()))
    if data:
        raw_text.pop(" ")
    raw_data = list(raw_text.items())
    val_dict = {str(i): {raw_data[i]} for i in range(len(raw_data))}
    return list(chunk_data(val_dict))
