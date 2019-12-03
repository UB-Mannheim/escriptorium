from django import template
from  django.utils import timezone

register = template.Library()


@register.simple_tag
def current_time():
    return timezone.now().isoformat()


@register.simple_tag
def line_break(lines):
    return "{} \n".format(lines)

# coordinates in pagexml template <TextRegion coords ="x1,x2..xn,yn>
@register.simple_tag
def box_coordinates(box):
    return ' '.join(','.join(map(str, pt)) for pt in box)



