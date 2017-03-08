from django import template
from home.models import Advert


register = template.Library()

@register.inclusion_tag('home/tags/adverts.html', takes_context=True)
def adverts(context):
    return {
        'adverts': Advert.objects.all(),
        'request': context['request'],
    }
