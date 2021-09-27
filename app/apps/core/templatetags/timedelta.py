from django import template


register = template.Library()

@register.filter()
def format_timedelta(td):
    if not td:
        return "Ø"

    seconds = td.total_seconds()
    formatted = ""

    if seconds > 86400:
        days = seconds // 86400
        formatted += f"{int(days)}d"
        seconds = seconds - days*86400

    if seconds > 3600:
        hours = seconds // 3600
        formatted += f" {int(hours)}h"
        seconds = seconds - hours*3600

    if seconds > 60:
        minuts = seconds // 60
        formatted += f" {int(minuts)}m"
        seconds = seconds - minuts*60

    if seconds > 0:
        formatted += f" {int(seconds)}s"

    return formatted