from django import forms
from django.forms.renderers import TemplatesSetting


class BootstrapFormMixin():
    default_renderer = TemplatesSetting
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if not field.widget.is_hidden:
                field.widget.attrs.update({
                    'placeholder': field.label,
                    'title': field.label,
                    'class': 'form-control'
                })
                if field.widget.input_type in ['select', 'checkbox']:
                    field.widget.need_label = True

    def full_clean(self):
        super().full_clean()
        if self._errors:
            for name, error in self._errors.items():
                if not self.fields[name].widget.is_hidden:
                    self.fields[name].widget.attrs['class'] += ' is-invalid'
