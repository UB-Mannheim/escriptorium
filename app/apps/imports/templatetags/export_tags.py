from django import template
from django.utils import timezone

register = template.Library()


@register.simple_tag
def current_time():
    return timezone.now().isoformat()


@register.simple_tag
def line_break(lines):
    return "{} \n".format(lines)


@register.simple_tag
def box_coordinates(block, part):
    # coordinates in pagexml template <TextRegion coords ="x1,x2..xn,yn>
    if block is not None:
        return ' '.join(','.join(map(lambda x: str(int(x)), pt)) for pt in block.box)
    else:
        w, h = part.image.width, part.image.height
        return '0,0 %d,0 %d,%d 0,%d' % (w, w, h, h)


@register.simple_tag
def pagexml_points(points):
    return ' '.join(','.join(map(lambda x: str(int(x)), pt)) for pt in points)


@register.simple_tag
def alto_points(points):
    return ' '.join(' '.join(map(lambda x: '%g' % x, pt)) for pt in points)
