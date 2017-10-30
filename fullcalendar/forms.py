from django import forms
from django.forms import ModelForm
from pytz import utc

from .models import PublicEvent

class UTCPublicEventForm(ModelForm):
    '''a form that force time to be entered with UTC'''
    start = forms.DateTimeField(input_formats=['%d/%m/%Y %H:%M'], widget=forms.DateTimeInput(format='%d/%m/%Y %H:%M'))
    end = forms.DateTimeField(input_formats=['%d/%m/%Y %H:%M'], widget=forms.DateTimeInput(format='%d/%m/%Y %H:%M'))

    class Meta:
        model = PublicEvent
        fields = ('title', 'start', 'end', 'url', 'description')

    def clean(self):
        '''convert replace timezones to utc'''
        cleaned_data = self.cleaned_data
        cleaned_data['start'] = cleaned_data['start'].replace(tzinfo=utc)
        cleaned_data['end'] = cleaned_data['end'].replace(tzinfo=utc)
        return cleaned_data
