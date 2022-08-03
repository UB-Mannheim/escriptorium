from django import template
from django.utils import timezone

register = template.Library()


@register.simple_tag
def current_time():
    return timezone.now().isoformat()


@register.simple_tag
def pagexml_points(points):
    return ' '.join(','.join(map(lambda x: str(int(x)), pt)) for pt in points)


@register.simple_tag
def alto_points(points):
    return ' '.join(' '.join(map(lambda x: '%g' % x, pt)) for pt in points)
