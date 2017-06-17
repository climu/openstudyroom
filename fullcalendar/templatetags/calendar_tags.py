from django import template
from home.models import Advert
from fullcalendar.models import PublicEvent
from django.utils import timezone

register = template.Library()

@register.simple_tag()
def public_events():
    cal_events = PublicEvent.get_future_public_events().order_by('start')
    return cal_events

@register.simple_tag()
def get_now():
    return timezone.now()
