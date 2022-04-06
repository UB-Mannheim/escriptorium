from django import template

register = template.Library()


@register.filter
def level_to_color(tags):
    """
    map django.contrib.messages level to bootstraps color code
    """
    level_map = {
        'debug': 'dark',
        'info': 'info',
        'success': 'success',
        'warning': 'warning',
        'error': 'danger'
    }
    return level_map[tags]


@register.simple_tag
def render_field(field, group=False, **kwargs):
    tplt = template.loader.get_template('django/forms/widgets/field.html')
    if 'class' in kwargs and 'class' in field.field.widget.attrs:
        kwargs['class'] = field.field.widget.attrs['class'] + " " + kwargs['class']
    if 'help_text' in kwargs:
        field.help_text = kwargs.pop('help_text')

    try:
        field.field
    except AttributeError:
        raise ValueError(f'Unknown field {field}')
    else:
        field.field.widget.attrs.update(**{k.replace('_', '-'): v
                                           for k, v in kwargs.items()
                                           if isinstance(k, str)})

    context = {'field': field, 'group': group}
    return tplt.render(context)  # .mark_safe()
