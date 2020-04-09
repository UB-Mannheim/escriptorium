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
def box_coordinates(block, part):
    w, h = part.image.width, part.image.height
     # not dummy block
    if block is not None:
        return ' '.join(','.join(map(lambda x: str(int(x)), pt)) for pt in block.box)
    else:
        return '0,0 %d,0 %d,%d 0,%d' % (w, w, h, h)


@register.filter
def to_int(value):
    return int(value)

# for pagexml export only
@register.simple_tag
def pagexml_points(points):
    return ' '.join(','.join(map(lambda x: str(int(x)), pt)) for pt in points)

