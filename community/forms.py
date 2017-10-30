from django import forms
from django.forms import ModelForm

from league.models import User

from .models import Community

class AdminCommunityForm(ModelForm):
    class Meta:
        model = Community
        fields = ['name',
        'slug',
        'description',
        'private_description',
        'close',
        'private',
        'promote'
        ]

class CommunityForm(ModelForm):
    class Meta:
        model = Community
        fields = [
        'description',
        'private_description',
        'close',
        'private'
        ]

class CommunytyUserForm(forms.Form):
    username = forms.CharField(label='username')

    def clean_username(self):
        username = self.cleaned_data['username']
        if not User.objects.filter(username__iexact=username).exists():
            message = "We don't have a user with username" + username + "."
            raise forms.ValidationError(message)
        return username
