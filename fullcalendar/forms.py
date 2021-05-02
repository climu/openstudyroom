from django import forms
from django.forms import ModelForm
from pytz import utc

from .models import PublicEvent, Category

class UTCPublicEventForm(ModelForm):
    '''a form that force time to be entered with UTC'''
    start = forms.DateTimeField(input_formats=['%d/%m/%Y %H:%M'], widget=forms.DateTimeInput(format='%d/%m/%Y %H:%M'))
    end = forms.DateTimeField(input_formats=['%d/%m/%Y %H:%M'], widget=forms.DateTimeInput(format='%d/%m/%Y %H:%M'))

    class Meta:
        model = PublicEvent
        fields = ('title', 'start', 'end', 'url', 'description', 'category')

    def clean(self):
        '''convert replace timezones to utc'''
        cleaned_data = self.cleaned_data
        cleaned_data['start'] = cleaned_data['start'].replace(tzinfo=utc)
        cleaned_data['end'] = cleaned_data['end'].replace(tzinfo=utc)
        return cleaned_data

    def __init__(self, *args, **kwargs):
        """
        Init categories choices depending on community in kwargs
        """
        community_pk = kwargs.pop('community_pk', None)
        super(UTCPublicEventForm, self).__init__(*args, **kwargs)
        if self.instance.pk is None:
            # if we create new event, we check if community_pk was in kwargs
            if community_pk is None:
                categories = Category.objects.filter(community=None)
            else:
                categories = Category.objects.filter(community__pk=community_pk)
        else:
            categories = Category.objects.filter(community=self.instance.community)
        self.fields["category"].queryset = categories


class CategoryForm(ModelForm):
    class Meta:
        model = Category
        fields = ('name', 'color')
