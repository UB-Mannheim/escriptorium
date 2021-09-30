from django.forms.widgets import Input
from django.db.models import CharField


class ColorWidget(Input):
    input_type = 'color'
    template_name = 'core/widgets/color.html'


class ColorField(CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 7
        super(ColorField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs['widget'] = ColorWidget
        return super(ColorField, self).formfield(**kwargs)
