from django import template
from fullcalendar.models import PublicEvent, GameAppointmentEvent, AvailableEvent
from django.utils import timezone
import pytz
register = template.Library()


@register.simple_tag(takes_context=True)
def public_events(context):
    request = context['request']
    user = request.user
    events = list(PublicEvent.objects.all().order_by('-start')[:5])
    if user.is_authenticated and user.is_league_member():
        my_games = list(GameAppointmentEvent.get_future_games(user))
        events = my_games + events
        events = sorted(events, key=lambda k: k.start, reverse=True)[:5]
    return public_events


@register.simple_tag()
def get_now():
    return timezone.now()


@register.simple_tag()
def tz_offset():
    tz = timezone.get_current_timezone()
    return timezone.localtime(timezone.now(), tz).utcoffset().total_seconds()
