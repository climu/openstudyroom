from django import forms
from django.template.loader import render_to_string
from django.forms.fields import EMPTY_VALUES

class RangeWidget(forms.MultiWidget):
    template_name = "widgets/range_widget.html"

    class Media:
        css = {
            'all': ("//cdnjs.cloudflare.com/ajax/libs/bootstrap-slider/9.8.1/css/bootstrap-slider.min.css",),
        }
        js = ('//cdnjs.cloudflare.com/ajax/libs/bootstrap-slider/9.8.1/bootstrap-slider.min.js',)

    def __init__(self, min, max, *args, **kwargs):
        widgets = (forms.NumberInput, forms.NumberInput)
        self.min = min
        self.max = max
        super(RangeWidget, self).__init__(widgets=widgets, *args, **kwargs)


    def get_context(self, name, value, attrs, *args, **kwargs):
        context = super(RangeWidget, self).get_context(name, value, attrs)
        context['min'] = self.min
        context['max'] = self.max
        return context

    def decompress(self, value):
        return value



class RangeField(forms.MultiValueField):
    default_error_messages = {
        'invalid_start': 'Enter a valid start value.',
        'invalid_end': 'Enter a valid end value.',
    }

    def __init__(self, min=0, max=10, values=[0,10], *args, **kwargs):
        if not 'initial' in kwargs:
            kwargs['initial'] = values

        super(RangeField, self).__init__(
                fields=(forms.IntegerField(), forms.IntegerField()),
                widget=RangeWidget(min, max),
                *args, **kwargs
                )

    def compress(self, data_list):
        print(data_list)
        if data_list:
            return [self.fields[0].clean(data_list[0]),self.fields[1].clean(data_list[1])]

        return None
