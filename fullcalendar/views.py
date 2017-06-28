from django.shortcuts import render, get_object_or_404
from django.views.generic.edit import UpdateView, CreateView
from django.contrib.auth.decorators import user_passes_test, login_required
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from datetime import datetime, timedelta
import json
from django.utils.timezone import make_aware
from league.models import is_league_admin, is_league_member
from .forms import UTCPublicEventForm
from .models import PublicEvent, AvailableEvent, GameRequestEvent
from pytz import utc, timezone
from league.models import User
from postman.api import pm_broadcast
from django.template import loader


# Create your views here.


class PublicEventUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    form_class = UTCPublicEventForm
    model = PublicEvent
    template_name_suffix = '_update_form'

    def test_func(self):
        return self.request.user.is_authenticated() and self.request.user.user_is_league_admin()

    def get_login_url(self):
        return '/'


class PublicEventCreate(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = UTCPublicEventForm
    model = PublicEvent
    template_name_suffix = '_create_form'
    initial = {'start': datetime.now(),
               'end': datetime.now()}

    def test_func(self):
        return self.request.user.is_authenticated() and self.request.user.user_is_league_admin()

    def get_login_url(self):
        return '/'


def calendar_view(request):
    user = request.user
    if user.is_authenticated and user.user_is_league_member:
        template = 'fullcalendar/calendar_member.html'
    else:
        template = 'fullcalendar/calendar.html'
    return render(request, template, {'user': user, })


def json_feed(request):
    '''get all events for one user and serve a json.'''
    user = request.user
    if user.is_authenticated:
        tz = user.get_timezone()
    else:
        tz = utc
    # get public events for everyone
    public_events = PublicEvent.objects.all()
    data = []
    for event in public_events:
        dict = {
            'id': 'public:' + str(event.pk),
            'title': event.title,
            'start': event.start.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
            'end': event.end.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
            'is_new': False,
            'editable': False,
            'type': 'public',
        }
        if event.url:
            dict['url'] = event.url
        data.append(dict)
    # get user related available events
    if user.is_authenticated() and user.user_is_league_member():
        if json.loads(request.GET.get('me-av', False)):
            # his own availability
            me_available_events = AvailableEvent.objects.filter(user=user)
            for event in me_available_events:
                dict = {
                    'id': 'me-a:' + str(event.pk),
                    'pk': str(event.pk),
                    'title': 'I am available',
                    'start': event.start.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                    'end': event.end.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                    'is_new': False,
                    'editable': True,
                    'type': 'me-available',
                    'color': '#ffff80',
                    'className': 'me-available',
                }
                data.append(dict)
        # his game requests
        my_game_request = GameRequestEvent.objects.filter(sender=user)
        for event in my_game_request:
            dict = {
                'id': 'my-gr:' + str(event.pk),
                'pk': str(event.pk),
                'title': 'My game request',
                'start': event.start.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                'end': event.end.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                'is_new': False,
                'editable': False,
                'type': 'my-gr',
                'color': '#FF8800',
                'className': 'my-gr',
            }
            data.append(dict)
        # others availability
        if json.loads(request.GET.get('other-av', False)):

            leagues_list = json.loads(request.GET.get('divs', ''))
            events = AvailableEvent.get_formated_other_available(user, leagues_list)
            for event in events:
                # event is formated like this:
                # { start: datetime,
                #   end : datetime,
                #   users: [user1, user2, ...]
                # }
                n_users = len(event['users'])
                dict = {
                    'id': 'other-available',
                    'title': str(n_users) + ' players available.',
                    'start': event['start'].astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                    'end': event['end'].astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                    'is_new': False,
                    'editable': False,
                    'type': 'other-available',
                    'color': '#01DF3A',
                    'className': 'other-available',
                    'rendering': 'background',
                    'users': event['users'],
                }
                data.append(dict)

    return HttpResponse(json.dumps(data), content_type="application/json")


@login_required()
@user_passes_test(is_league_member, login_url="/", redirect_field_name=None)
def create_game_request(request):
    """Create a game request from calendar ajax post."""
    sender = request.user
    tz = sender.get_timezone()
    return HttpResponse('success')

    if request.method == 'POST':
        users_list = json.loads(request.POST.get('users'))
        date = datetime.strptime(request.POST.get('date'), '%Y-%m-%dT%H:%M:%S')
        date = make_aware(date, tz)
        receivers = User.objects.filter(kgs_username__in=users_list)

        # a game request should last 1h30
        end = date + timedelta(hours=1, minutes=30)
        # create the instance
        request = GameRequestEvent(start=date, end=end, sender=sender)
        request.save()
        request.receivers = receivers
        request.save()

        # send a message to all receivers
        subject = 'Game request from' + sender.kgs_username \
            + ' on ' + date.strftime('%d %b')
        plaintext = loader.get_template('fullcalendar/messages/game_request.txt')
        context = {
            'sender': sender,
            'date': date
        }
        message = plaintext.render(context)
        pm_broadcast(
            sender=sender,
            recipients=list(receivers),
            subject=subject
            ,body=message
        )

        return HttpResponse('success')




@login_required()
@user_passes_test(is_league_member, login_url="/", redirect_field_name=None)
def save(request):
    """Get events modification from calendar ajax post."""
    user = request.user
    tz = user.get_timezone()
    if request.method == 'POST':
        changed_events = ''
        changed_events = json.loads(request.POST.get('events'))
        for event in changed_events:
            if event['type'] == 'deleted':  # we deleted an event
                pk = event['pk']
                if event['id'].startswith('me-a'):
                    # we had user=user to be sure one user can only delete his available events
                    ev = get_object_or_404(AvailableEvent, user=user, pk=pk)
                    ev.delete()

            elif event['is_new']:  # we create a new event on server
                start = datetime.strptime(event['start'], '%Y-%m-%dT%H:%M:%S')
                start = make_aware(start, tz)
                end = datetime.strptime(event['end'], '%Y-%m-%dT%H:%M:%S')
                end = make_aware(end, tz)
                if event['type'] == 'me-available':
                    AvailableEvent.objects.create(start=start, end=end, user=user)

            else:  # the event must have been moved or resized.
                start = datetime.strptime(event['start'], '%Y-%m-%dT%H:%M:%S')
                start = make_aware(start, tz)
                end = datetime.strptime(event['end'], '%Y-%m-%dT%H:%M:%S')
                end = make_aware(end, tz)
                pk = event['pk']
                if event['type'] == 'me-available':
                    ev = get_object_or_404(AvailableEvent, user=user, pk=pk)
                    ev.start = start
                    ev.end = end
                    ev.save()

    return HttpResponse('success')


@login_required()
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def admin_cal_event_list(request):
    public_events = PublicEvent.objects.all()
    return render(request, 'fullcalendar/admin_cal_event_list.html', {'public_events': public_events, })


@login_required()
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def admin_delete_event(request, pk):
    if request.method == 'POST':
        event = get_object_or_404(PublicEvent, pk=pk)
        event.delete()
    else:
        raise Http404("What are you doing here ?")
    return HttpResponseRedirect(reverse('calendar:admin_cal_event_list'))
