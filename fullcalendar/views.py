from django.shortcuts import render, get_object_or_404
from django.views.generic.edit import UpdateView, CreateView
from django.contrib.auth.decorators import user_passes_test, login_required
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from datetime import datetime, timedelta
import json
from django.utils.timezone import make_aware
from league.models import User, is_league_admin, is_league_member
from .forms import UTCPublicEventForm
from .models import PublicEvent, AvailableEvent, GameRequestEvent, GameAppointmentEvent
from pytz import utc
from django.utils import timezone
from postman.api import pm_broadcast, pm_write
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
        context = {
            'user': user,
            'start_time_range': user.profile.start_cal,
            'end_time_range': user.profile.end_cal
        }
    else:
        template = 'fullcalendar/calendar.html'
        context = {'user': user}
    return render(request, template, context)


def json_feed(request):
    """get all events for one user and serve a json."""
    user = request.user
    if user.is_authenticated:
        tz = user.get_timezone()
    else:
        tz = utc

    start = datetime.strptime(request.GET.get('start'), '%Y-%m-%d')
    start = make_aware(start, tz)
    end = datetime.strptime(request.GET.get('end'), '%Y-%m-%d')
    end = make_aware(end, tz)

    # get public events for everyone
    public_events = PublicEvent.objects.filter(end__gte=start, start__lte=end)
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
    # get user related available events and game requests
    if user.is_authenticated() and user.user_is_league_member():
        now = timezone.now()
        # Games appointments
        game_appointments = user.fullcalendar_gameappointmentevent_related.filter(
            start__gte=now
        )
        for event in game_appointments:
            opponent = event.opponent(user)
            dict = {
                'id': 'game:' + str(event.pk),
                'pk': event.pk,
                'title': 'Game vs ' + opponent.kgs_username,
                'start': event.start.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                'end': event.end.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                'is_new': False,
                'editable': False,
                'type': 'game',
                'color': '#ff4444'
            }
            data.append(dict)
        if json.loads(request.GET.get('me-av', False)):
            # his own availability
            me_available_events = AvailableEvent.objects.filter(
                user=user,
                end__gte=now,
                start__lte=end,
            )
            for event in me_available_events:
                dict = {
                    'id': 'me-a:' + str(event.pk),
                    'pk': str(event.pk),
                    'title': 'I am available',
                    'start': event.start.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                    'end': event.end.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                    'is_new': False,
                    'type': 'me-available',
                    'color': '#ffff80',
                    'className': 'me-available',
                }
                if json.loads(request.GET.get('other-av', False)):
                    dict['rendering'] = 'background'
                else:
                    dict['editable'] = True

                data.append(dict)




        # others availability
        if json.loads(request.GET.get('other-av', False)):

            leagues_list = json.loads(request.GET.get('divs', ''))
            events = AvailableEvent.get_formated_other_available(
                user,
                leagues_list
            )
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

        # Game requests
        if json.loads(request.GET.get('game-request', False)):
            # his game requests
            my_game_request = GameRequestEvent.objects.filter(
                sender=user,
                end__gte=now,
                start__lte=end,
            )
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
                    'users': list(u.kgs_username for u in event.receivers.all())
                }
                data.append(dict)

            # others game requests
            others_game_requests = GameRequestEvent.objects.filter(
                receivers=user,
                start__lte=end,
                end__gte=now,
            )
            for event in others_game_requests:
                dict = {
                    'id': 'other-gr:' + str(event.pk),
                    'pk': str(event.pk),
                    'title': event.sender.kgs_username + ' game request',
                    'start': event.start.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                    'end': event.end.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                    'is_new': False,
                    'editable': False,
                    'type': 'other-gr',
                    'color': '#009933',
                    'className': 'other-gr',
                    'sender': event.sender.kgs_username
                }
                data.append(dict)

    return HttpResponse(json.dumps(data), content_type="application/json")

@login_required()
@user_passes_test(is_league_member, login_url="/", redirect_field_name=None)
def update_time_range_ajax(request):
    if request.method == 'POST':
        start = request.POST.get('start')
        end = request.POST.get('end')
        request.user.profile.start_cal = start
        request.user.profile.end_cal = end
        request.user.profile.save()
        return HttpResponse('success')


@login_required()
@user_passes_test(is_league_member, login_url="/", redirect_field_name=None)
def cancel_game_ajax(request):
    """Cancel a game appointment from calendar ajax post."""
    user = request.user
    if request.method == 'POST':
        pk = int(request.POST.get('pk'))
        game_appointment = get_object_or_404(GameAppointmentEvent, pk=pk)
        if user in game_appointment.users.all():
            opponent = game_appointment.opponent(user)
            game_appointment.delete()
            # send a message
            subject = user.kgs_username + ' has cancel your game appointment.'
            plaintext = loader.get_template('fullcalendar/messages/game_cancel.txt')
            context = {
                'user': user,
                'date': game_appointment.start
            }
            message = plaintext.render(context)
            pm_write(
                sender=user,
                recipient=opponent,
                subject=subject,
                body=message,
                skip_notification=True
            )
            return HttpResponse('success')

@login_required()
@user_passes_test(is_league_member, login_url="/", redirect_field_name=None)
def accept_game_request_ajax(request):
    """accept a game request from calendar ajax post."""
    user = request.user
    if request.method == 'POST':
        pk = int(request.POST.get('pk'))
        game_request = get_object_or_404(GameRequestEvent, pk=pk)
        sender = game_request.sender
        game_appointment = GameAppointmentEvent(
            start=game_request.start,
            end=game_request.end
        )
        game_appointment.save()
        game_appointment.users.add(user, sender)
        game_request.delete()
        # send a message
        subject = user.kgs_username + ' has accepted your game request.'
        plaintext = loader.get_template('fullcalendar/messages/game_request_accepted.txt')
        context = {
            'user': user,
            'date': game_appointment.start
        }
        message = plaintext.render(context)
        pm_write(
            sender=user,
            recipient=sender,
            subject=subject,
            body=message,
            skip_notification=True
        )
        return HttpResponse('success')

@login_required()
@user_passes_test(is_league_member, login_url="/", redirect_field_name=None)
def reject_game_request_ajax(request):
    """Reject a game request from calendar ajax post."""
    user = request.user
    if request.method == 'POST':
        pk = int(request.POST.get('pk'))
        game_request = get_object_or_404(GameRequestEvent, pk=pk)
        game_request.receivers.remove(user)

        if game_request.receivers.count() == 0:
            game_request.delete()
        return HttpResponse('success')
    else:
        return HttpResponse('error')


@login_required()
@user_passes_test(is_league_member, login_url="/", redirect_field_name=None)
def cancel_game_request_ajax(request):
    """Cancel a game request from calendar ajax post."""
    user = request.user
    if request.method == 'POST':
        pk = int(request.POST.get('pk'))
        game_request = get_object_or_404(GameRequestEvent, pk=pk)
        # A user should only cancel his own game requests
        if game_request.sender == user:
            game_request.delete()
            return HttpResponse('success')
        else:
            return HttpResponse('error')

@login_required()
@user_passes_test(is_league_member, login_url="/", redirect_field_name=None)
def create_game_request(request):
    """Create a game request from calendar ajax post."""
    sender = request.user
    tz = sender.get_timezone()
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
        subject = 'Game request from ' + sender.kgs_username \
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
            subject=subject,
            body=message,
            skip_notification=True
        )

        return HttpResponse('success')


@login_required()
@user_passes_test(is_league_member, login_url="/", redirect_field_name=None)
def game_request_list(request):
    user = request.user
    game_requests = GameRequestEvent.objects.filter(receivers=user,)

@login_required()
@user_passes_test(is_league_member, login_url="/", redirect_field_name=None)
def save(request):
    """Get events modification from calendar ajax post."""
    user = request.user
    tz = user.get_timezone()
    now = timezone.now()
    if request.method == 'POST':
        changed_events = ''
        changed_events = sorted(
            json.loads(request.POST.get('events')),
            key=lambda k: k['end']
        )
        prev_event = None
        for event in changed_events:
            start = datetime.strptime(event['start'], '%Y-%m-%dT%H:%M:%S')
            start = make_aware(start, tz)
            end = datetime.strptime(event['end'], '%Y-%m-%dT%H:%M:%S')
            end = make_aware(end, tz)
            if event['type'] == 'deleted':  # we deleted an event
                pk = event['pk']
                if event['id'].startswith('me-a'):
                    # we had user=user to be sure one user can only delete his available events
                    ev = get_object_or_404(AvailableEvent, user=user, pk=pk)
                    ev.delete()

            elif event['is_new']:  # we create a new event on server
                if end > now:
                    if event['type'] == 'me-available':
                        # If this event start exactly at the same time as the
                        # previous event ended, we just merge those events.
                        if prev_event is not None and start == prev_event.end:
                            prev_event.end = end
                            prev_event.save()

                        else:
                            new_event = AvailableEvent.objects.create(
                                start=start,
                                end=end,
                                user=user
                                )
                            prev_event = new_event

            elif end > now:  # the event must have been moved or resized.
                pk = event['pk']
                if event['type'] == 'me-available':
                    if prev_event is not None and start == prev_event.end:
                        prev_event.end = end
                        prev_event.save()
                        ev = get_object_or_404(AvailableEvent, user=user, pk=pk)
                        ev.delete()

                    else:
                        ev = get_object_or_404(AvailableEvent, user=user, pk=pk)
                        ev.start = start
                        ev.end = end
                        ev.save()
                        prev_event = ev


    return HttpResponse('success')


@login_required()
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def admin_cal_event_list(request):
    public_events = PublicEvent.objects.all()
    return render(
        request,
        'fullcalendar/admin_cal_event_list.html',
        {'public_events': public_events, }
    )


@login_required()
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def admin_delete_event(request, pk):
    if request.method == 'POST':
        event = get_object_or_404(PublicEvent, pk=pk)
        event.delete()
    else:
        raise Http404("What are you doing here ?")
    return HttpResponseRedirect(reverse('calendar:admin_cal_event_list'))
