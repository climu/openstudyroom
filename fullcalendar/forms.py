from django import forms
from django.forms import ModelForm, Textarea
from .models import CalEvent



class CalEventForm(ModelForm):

    class Meta:
        model = CalEvent
        fields = ('title','begin_time', 'end_time','url','description')
    
