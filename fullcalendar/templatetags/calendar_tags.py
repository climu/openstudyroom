from django import template
from home.models import Advert
from fullcalendar.models import CalEvent
from django.utils import timezone

register = template.Library()

@register.simple_tag()
def cal_events(user):
    cal_events = CalEvent.get_future_cal_events(user).order_by('-begin_time')
    return cal_events

@register.simple_tag()
def get_now():
    return timezone.now()
