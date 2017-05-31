from django import forms
from django.forms import ModelForm, Textarea
from .models import CalEvent
from django.utils import timezone
from time import gmtime, strftime
from datetime import datetime
from pytz import utc

class UTCCalEventForm(ModelForm):
    '''a form that force time to be entered with UTC'''
    begin_time = forms.DateTimeField(input_formats=['%d/%m/%Y %H:%M'], widget=forms.DateTimeInput(format='%d/%m/%Y %H:%M'))
    end_time = forms.DateTimeField(input_formats=['%d/%m/%Y %H:%M'], widget=forms.DateTimeInput(format='%d/%m/%Y %H:%M'))

    class Meta:
        model = CalEvent
        fields = ('title','begin_time', 'end_time','url','description')

    def clean(self):
        '''convert replace timezones to utc'''
        cleaned_data = self.cleaned_data
        cleaned_data['begin_time'] = cleaned_data['begin_time'].replace(tzinfo=utc)
        cleaned_data['end_time'] = cleaned_data['end_time'].replace(tzinfo=utc)
        return cleaned_data
