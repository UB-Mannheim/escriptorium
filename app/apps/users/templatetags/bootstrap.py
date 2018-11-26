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
