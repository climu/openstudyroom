from django import template
from django.utils import timezone
from fullcalendar.models import PublicEvent, GameAppointmentEvent

register = template.Library()


@register.simple_tag(takes_context=True)
def public_events(context):
    request = context['request']
    user = request.user
    events = list(PublicEvent.objects.filter(community=None).order_by('-start')[:5])
    if user.is_authenticated and user.is_league_member():
        my_games = list(GameAppointmentEvent.get_future_games(user))
        events = my_games + events
        communities = user.get_communities()
        for community in communities:
            events += list(community.publicevent_set.order_by('-start')[:5])
        events = sorted(events, key=lambda k: k.start, reverse=True)[:5]
    return events


@register.simple_tag()
def get_now():
    return timezone.now()


@register.simple_tag()
def tz_offset():
    tz = timezone.get_current_timezone()
    return timezone.localtime(timezone.now(), tz).utcoffset().total_seconds()
