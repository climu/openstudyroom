from django import template
from home.models import Advert
from fullcalendar.models import PublicEvent, GameAppointmentEvent
from django.utils import timezone

register = template.Library()

@register.simple_tag(takes_context=True)
def public_events(context):
    request = context['request']
    user = request.user
    public_events = PublicEvent.get_future_public_events().order_by('start')
    if user.is_authenticated and user.user_is_league_admin():
        my_games = list(GameAppointmentEvent.get_future_games(user))
        public_events = list(PublicEvent.get_future_public_events())
        cal_events = my_games + public_events
        cal_events = sorted(cal_events, key=lambda k: k.start)
        return cal_events
    else:
        return public_events


@register.simple_tag()
def get_now():
    return timezone.now()
