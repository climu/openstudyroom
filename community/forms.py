from django import forms
from django.contrib.auth import get_user_model
from django.forms import ModelForm
from .models import Community
from league.models import User

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
