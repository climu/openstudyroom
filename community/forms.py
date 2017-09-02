from django import forms
from django.contrib.auth import get_user_model
from django.forms import ModelForm
from .models import Community

class AdminCommunityForm(ModelForm):
    class Meta:
        model = Community
        fields = ['name',
        'description',
        'close',
        'private'
        ]

class CommunityForm(ModelForm):
    class Meta:
        model = Community
        fields = [
        'description',
        'close',
        'private'
        ]
