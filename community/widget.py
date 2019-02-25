from django import forms
from .models import Community


class Community_select(forms.CheckboxSelectMultiple):
    template_name = "community/includes/community_widget_checkbox.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        communities = Community.objects.filter(private=False)
        context['communities'] = communities
        return context
