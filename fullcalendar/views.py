from datetime import datetime, timedelta
import json
import vobject

from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.views.generic.edit import UpdateView, CreateView
from django.contrib.auth.decorators import user_passes_test, login_required
from django.http import Http404, HttpResponseRedirect, HttpResponse, JsonResponse, \
    HttpResponseForbidden
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.utils.timezone import make_aware
from django.utils import timezone
from django.template import loader
from django.views.decorators.http import require_POST
from postman.api import pm_broadcast, pm_write
from pytz import utc

from community.models import Community
from league.models import User, LeagueEvent, Division
from league.forms import ActionForm
from .forms import UTCPublicEventForm, CategoryForm
from .models import PublicEvent, AvailableEvent, GameRequestEvent, GameAppointmentEvent, Category


class CategoryCreate(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = CategoryForm
    model = Category
    template_name_suffix = '_create_form'

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_osr_admin()

    def get_login_url(self):
        return '/'

class CategoryUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    form_class = CategoryForm
    model = Category
    template_name_suffix = '_update_form'

    def test_func(self):
        return self.get_object().can_edit(self.request.user)

    def get_login_url(self):
        return '/'

    def get_success_url(self):
        return self.get_object().get_redirect_url()

class PublicEventUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    form_class = UTCPublicEventForm
    model = PublicEvent
    template_name_suffix = '_update_form'

    def test_func(self):
        return self.get_object().can_edit(self.request.user)

    def get_login_url(self):
        return '/'

    def get_success_url(self):
        return self.get_object().get_redirect_url()


class PublicEventCreate(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = UTCPublicEventForm
    model = PublicEvent
    template_name_suffix = '_create_form'

    initial = {'start': datetime.now(),
               'end': datetime.now()}

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_osr_admin()

    def get_login_url(self):
        return '/'

def calendar_view(request, user_id=None):
    if user_id is None:
        user = request.user
    else:
        user = get_object_or_404(User, pk=user_id)

    # public calendar for unauth users
    if not request.user.is_authenticated:
        template = 'fullcalendar/calendar.html'
        context = {'user': user}
    # Own calendar for OSR members
    elif user == request.user and user.is_league_member:
        template = 'fullcalendar/calendar_member.html'
        context = {
            'user': user,
            'start_time_range': user.profile.start_cal,
            'end_time_range': user.profile.end_cal
        }
    # Other members calendar
    else:
        template = 'fullcalendar/calendar_other_member.html'
        context = {
            'user': user,
            'start_time_range': request.user.profile.start_cal,
            'end_time_range': request.user.profile.end_cal
        }
    return render(request, template, context)


@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def json_feed_other(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    # get user timezone
    tz = request.user.get_timezone()

    # Get start and end from request and use user tz
    start = datetime.strptime(request.GET.get('start'), '%Y-%m-%d')
    start = make_aware(start, tz)
    end = datetime.strptime(request.GET.get('end'), '%Y-%m-%d')
    end = make_aware(end, tz)

    # get public events
    data = PublicEvent.get_formated_public_event(start, end, tz)

    now = timezone.now()
    # Games appointments
    data += GameAppointmentEvent.get_formated_game_appointments(user, now, tz)
    # User's availability
    available_events = AvailableEvent.objects.filter(
        user=user,
        end__gte=now,
        start__lte=end,
    )
    for event in available_events:
        dict = {
            'id': 'user-a:' + str(event.pk),
            'pk': str(event.pk),
            'title': user.username + ' is available',
            'start': event.start.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
            'end': event.end.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
            'is_new': False,
            'type': 'other-available',
            'color': '#01DF3A',
            'className': 'other-available',
            'rendering': 'background',
            'users': [user.username],
        }
        data.append(dict)

    # Game requests
        # sent by request.user
    my_game_request = GameRequestEvent.objects.filter(
        sender=request.user,
        receivers=user,
        end__gte=now,
        start__lte=end,
    ).prefetch_related('receivers')

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
            'users': list(u.username for u in event.receivers.all())
        }
        data.append(dict)

        # sent by user
    his_game_requests = GameRequestEvent.objects.filter(
            sender=user,
            receivers=request.user,
            end__gte=now,
            start__lte=end,
    )

    for event in his_game_requests:
        dict = {
            'id': 'other-gr:' + str(event.pk),
            'pk': str(event.pk),
            'title': event.sender.username + ' game request',
            'start': event.start.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
            'end': event.end.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
            'is_new': False,
            'editable': False,
            'type': 'other-gr',
            'color': '#009933',
            'className': 'other-gr',
            'sender': user.username
        }
        data.append(dict)
    return JsonResponse(data, safe=False)

def parseFCalendarDate(str, tz):
    date = datetime.strptime(str, '%Y-%m-%dT%H:%M:%SZ')
    date = make_aware(date, tz)
    return date

def calendar_main_view(request):
    user = request.user
    now = timezone.now()

    # Served data for front end application
    calendar_data = {}
    context = {}

    # Get all active leagues
    active_leagues = LeagueEvent.objects.filter(
        end_time__gte=now)

    if user.is_authenticated:
        calendar_data['user'] = user.format()
        start_time_range = user.profile.start_cal
        end_time_range = user.profile.end_cal

        # Get all public communities and those the user is member of
        user_communities = user.groups.filter(
            name__endswith='community_member')
        communities = Community.objects.filter(
            Q(private=False) | Q(user_group__in=user_communities))

        # Get all public leagues and those the user is member of
        user_divisions = user.get_active_divisions()
        leagues = active_leagues.filter(
            Q(is_public=True) | Q(division__in=user_divisions)).distinct()

        user_opponents = user.get_opponents_for_calendar()
        context['user'] = user
        context['user_divisions'] = user_divisions
        context['user_opponents'] = user_opponents

    else:
        start_time_range = 0
        end_time_range = 24
        communities = Community.objects.filter(private=False)
        leagues = active_leagues.filter(is_public=True)

    calendar_data['communities'] = [c.format() for c in communities]
    calendar_data['leagues'] = [l.format() for l in leagues]

    context['communities'] = communities
    context['leagues'] = leagues
    context['start_time_range'] = start_time_range
    context['end_time_range'] = end_time_range
    context['calendar_data'] = calendar_data

    return render(request, 'fullcalendar/calendar2.html', context)

def get_public_events(request):
    """
    Returns all public events inside a range period.
    If you may ask, community filtering now occurs
    in client side.
    """
    user = request.user
    tz = user.get_timezone() if user.is_authenticated else utc
    end = parseFCalendarDate(request.GET.get('end'), tz)
    events = PublicEvent.get_formated(end, tz)
    return JsonResponse(events, safe=False)

def get_available_events(request, user_pk):
    """
    Returns all available events of the user inside
    a range period.
    """
    user = get_object_or_404(User, pk=user_pk)
    tz = request.user.get_timezone() if request.user.is_authenticated else utc
    end = parseFCalendarDate(request.GET.get('end'), tz)
    events = AvailableEvent.get_formated_user(user, end, tz)
    return JsonResponse(events, safe=False)

def get_opponents_available_events(request, user_pk):
    """
    Returns all available events of user's opponents
    inside a range period.
    """
    user = get_object_or_404(User, pk=user_pk)
    tz = request.user.get_timezone() if request.user.is_authenticated else utc
    end = parseFCalendarDate(request.GET.get('end'), tz)
    leagues = json.loads(request.GET.get('leagues'))
    events = AvailableEvent.get_formated_opponents(user, end, leagues)
    return JsonResponse(events, safe=False)

@user_passes_test(User.is_league_member)
def get_game_request_events(request):
    """
    Returns all users's game requests inside a range period.
    """
    user = request.user
    tz = user.get_timezone()
    start = parseFCalendarDate(request.GET.get('start'), tz)
    end = parseFCalendarDate(request.GET.get('end'), tz)
    events = GameRequestEvent.get_formated(user, start, end, tz)
    return JsonResponse(events, safe=False)

def get_game_appointment_events(request):
    tz = request.user.get_timezone() if request.user.is_authenticated else utc
    events = GameAppointmentEvent.get_formated(tz, request.user if request.user.is_authenticated else None)
    return JsonResponse(events, safe=False)

@require_POST
@login_required()
@user_passes_test(User.is_league_member)
def create_available_event(request):
    user = request.user
    tz = user.get_timezone()
    start = parseFCalendarDate(request.POST.get('start'), tz)
    end = parseFCalendarDate(request.POST.get('end'), tz)
    user_availabilities = AvailableEvent.objects.filter(
        user=user,
        end__gte=timezone.now(),
        start__lte=end)
    # merge overlapping events
    startTimes = [start]
    endTimes = [end]
    for event in user_availabilities:
        if start < event.end and event.start < end:
            startTimes.append(event.start)
            endTimes.append(event.end)
            event.delete()
    new_event = AvailableEvent.objects.create(
        start=min(startTimes),
        end=max(endTimes),
        user=user)
    # check if borns are equals with other event in
    # user_availabilities (basically the ones not deleted)
    new_event.save()
    return HttpResponse('success')

@require_POST
@login_required()
@user_passes_test(User.is_league_member)
def update_available_event(request):
    user = request.user
    pk = request.POST.get('pk')
    updatedEvent = get_object_or_404(AvailableEvent, pk=pk)
    tz = user.get_timezone()
    start = parseFCalendarDate(request.POST.get('start'), tz)
    end = parseFCalendarDate(request.POST.get('end'), tz)
    user_availabilities = AvailableEvent.objects.filter(user=user).exclude(pk=pk)
    # merge overlapping events
    startTimes = [start]
    endTimes = [end]
    for event in user_availabilities:
        if start < event.end and event.start < end:
            startTimes.append(event.start)
            endTimes.append(event.end)
            event.delete()
    updatedEvent.start = min(startTimes)
    updatedEvent.end = max(endTimes)
    updatedEvent.save()
    return HttpResponse('success')

@require_POST
@login_required()
@user_passes_test(User.is_league_member)
def delete_available_event(request):
    user = request.user
    pk = request.POST.get('pk')
    ev = get_object_or_404(AvailableEvent, user=user, pk=pk)
    ev.delete()
    return HttpResponse('success')

def json_feed(request):
    """get all events for one user and serve a json."""
    user = request.user
    # get user timezone
    if user.is_authenticated:
        tz = user.get_timezone()
    else:
        tz = utc

    # Get start and end from request and use user tz
    start = datetime.strptime(request.GET.get('start'), '%Y-%m-%d')
    start = make_aware(start, tz)
    end = datetime.strptime(request.GET.get('end'), '%Y-%m-%d')
    end = make_aware(end, tz)

    # if community in request.GET, we only return community related events
    community_pk = request.GET.get('community', None)
    if community_pk == '':
        community_pk = None

    # get public events for everyone
    data = PublicEvent.get_formated_public_event(start, end, tz, community_pk)

    # get user related available events and game requests
    if user.is_authenticated and user.is_league_member():
        now = timezone.now()
        # if community is None (general calendar) and user is auth,
        # we also show in their calendar their community related events
        if community_pk is None:
            for comm in user.get_communities():
                data += PublicEvent.get_formated_public_event(start, end, tz, comm.pk)

        # Games appointments
        data += GameAppointmentEvent.get_formated_game_appointments(user, now, tz)

        if request.GET.get('me-av', False):
            # his own availability
            me_available_events = AvailableEvent.objects.filter(
                user=user,
                end__gte=now,
                start__lte=end,
            )
            data += AvailableEvent.format_me_availables(
                me_available_events,
                json.loads(request.GET.get('other-av', False)),
                tz
            )

        # others availability
        if request.GET.get('other-av', False):
            if 'servers' in request.GET:
                server_list = json.loads(request.GET.get('servers'))
            else:
                server_list = None
            if 'divs' in request.GET:
                leagues_list = json.loads(request.GET.get('divs'))
            else:
                leagues_list = None

            events = AvailableEvent.get_formated_other_available(
                user,
                leagues_list,
                server_list
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
        if request.GET.get('game-request', False):
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
                    'users': list(u.username for u in event.receivers.all())
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
                    'title': event.sender.username + ' game request',
                    'start': event.start.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                    'end': event.end.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                    'is_new': False,
                    'editable': False,
                    'type': 'other-gr',
                    'color': '#009933',
                    'className': 'other-gr',
                    'sender': event.sender.username
                }
                data.append(dict)
    return JsonResponse(data, safe=False)


@require_POST
@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def update_time_range_ajax(request):
    start = request.POST.get('start')
    end = request.POST.get('end')
    request.user.profile.start_cal = start
    request.user.profile.end_cal = end
    request.user.profile.save()
    return HttpResponse('success')


@require_POST
@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def cancel_game_ajax(request):  # pylint: disable=inconsistent-return-statements
    """Cancel a game appointment from calendar ajax post."""
    user = request.user
    pk = int(request.POST.get('pk'))
    game_appointment = get_object_or_404(GameAppointmentEvent, pk=pk)
    if user in game_appointment.users.all():
        opponent = game_appointment.opponent(user)
        game_appointment.delete()
        # send a message
        subject = user.username + ' has cancel your game appointment.'
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
            skip_notification=False
        )
        return HttpResponse('success')
    return HttpResponseForbidden()


@require_POST
@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def accept_game_request_ajax(request):
    """accept a game request from calendar ajax post."""
    user = request.user
    pk = int(request.POST.get('pk'))
    game_request = get_object_or_404(GameRequestEvent, pk=pk)
    sender = game_request.sender
    private = game_request.private
    divisions = game_request.divisions.all()
    GameAppointmentEvent.create(sender, user, divisions, private, game_request.start, game_request.end, True)
    game_request.delete()
    return HttpResponse('success')

@require_POST
@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def reject_game_request_ajax(request):
    """Reject a game request from calendar ajax post."""
    user = request.user
    pk = int(request.POST.get('pk'))
    game_request = get_object_or_404(GameRequestEvent, pk=pk)
    game_request.receivers.remove(user)
    if game_request.receivers.count() == 0:
        game_request.delete()
    return HttpResponse('success')

@require_POST
@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def cancel_game_request_ajax(request):
    """Cancel a game request from calendar ajax post."""
    user = request.user
    pk = int(request.POST.get('pk'))
    game_request = get_object_or_404(GameRequestEvent, pk=pk, sender=user)
    game_request.delete()
    return HttpResponse('success')

@require_POST
@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def create_game(request):
    """
    Create a game request/appointment based of request.POST.type.
    Plan to use Django form validation.
    """
    sender = request.user
    tz = sender.get_timezone()
    start = parseFCalendarDate(request.POST.get('date'), tz)
    receiver = json.loads(request.POST.get('receiver'))
    divisions = json.loads(request.POST.get('divisions'))
    private = json.loads(request.POST.get('private'))
    type = request.POST.get('type')
    receiver = User.objects.get(pk=receiver)
    divisions = Division.objects.filter(pk__in=divisions)
    # a game should last 1h30
    end = start + timedelta(hours=1, minutes=30)

    if type == 'game-request':
        GameRequestEvent.create(
            sender, receiver, divisions, private, start, end)
    else: #type == 'game-appointment':
        GameAppointmentEvent.create(
            sender, receiver, divisions, private, start, end)
    return HttpResponse('success')

@require_POST
@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def create_game_request(request):
    """Create a game request from calendar ajax post."""
    sender = request.user
    tz = sender.get_timezone()
    users_list = json.loads(request.POST.get('users'))
    date = datetime.strptime(request.POST.get('date'), '%Y-%m-%dT%H:%M:%S')
    date = make_aware(date, tz)
    receivers = User.objects.filter(username__in=users_list)
    if not receivers:
        return HttpResponse('error')
    # a game request should last 1h30
    end = date + timedelta(hours=1, minutes=30)
    # create the instance
    game_request = GameRequestEvent(start=date, end=end, sender=sender)
    game_request.save()
    game_request.receivers.add(*receivers)
    game_request.save()

    # send a message to all receivers
    subject = 'Game request from ' + sender.username \
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
        skip_notification=False
    )

    return HttpResponse('success')


@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def save(request):
    """Get events modification from calendar ajax post."""
    user = request.user
    tz = user.get_timezone()
    now = timezone.now()
    to_announce = []
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
                if end > now and event['type'] == 'me-available':
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
                        # add the event in the announce list
                        to_announce.append(new_event)

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

    # Announce nex available events
    AvailableEvent.annonce_on_discord(to_announce)
    return HttpResponse('success')


@login_required()
@user_passes_test(User.is_osr_admin, login_url="/", redirect_field_name=None)
def admin_cal_event_list(request):
    public_events = PublicEvent.objects.filter(community=None).order_by('-end')
    categories = Category.objects.filter(community=None)
    return render(
        request,
        'fullcalendar/admin_cal_event_list.html',
        {'public_events': public_events, 'categories': categories}
    )

@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def admin_delete_category(request, pk):
    if request.method == 'POST':
        event = get_object_or_404(Category, pk=pk)
        form = ActionForm(request.POST)
        if form.is_valid() and event.can_edit(request.user):
            url = event.get_redirect_url()
            event.delete()
            return HttpResponseRedirect(url)
    raise Http404("What are you doing here ?")

@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def admin_delete_event(request, pk):
    if request.method == 'POST':
        event = get_object_or_404(PublicEvent, pk=pk)
        form = ActionForm(request.POST)
        if form.is_valid() and event.can_edit(request.user):
            url = event.get_redirect_url()
            event.delete()
            return HttpResponseRedirect(url)
    raise Http404("What are you doing here ?")


@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def copy_previous_week_ajax(request):
    """ Reproduce the same availability as previous week. Ajax Yo !"""
    if request.method == 'POST':
        user = request.user
        tz = user.get_timezone()
        start = datetime.strptime(request.POST.get('start'), '%Y-%m-%d')
        start = make_aware(start, tz)
        end = datetime.strptime(request.POST.get('end'), '%Y-%m-%d')
        end = make_aware(end, tz)
        # First we test if current week is empty
        week_have_events = AvailableEvent.objects.filter(
            user=user,
            end__gte=start,
            start__lte=end,
        ).exists()
        if week_have_events:
            return HttpResponse('error:week is not empty')
        previous_events = AvailableEvent.objects.filter(
            user=user,
            end__gte=start - timedelta(days=7),
            start__lte=end - timedelta(days=7),
        )
        for event in previous_events:
            new_event = AvailableEvent(
                user=event.user,
                start=event.start + timedelta(days=7),
                end=event.end + timedelta(days=7)
            )
            new_event.save()
        return HttpResponse('success')
    else:
        return HttpResponse('error')


def ical(request, user_id):
    osr_events = PublicEvent.objects.all()
    user = get_object_or_404(User, pk=user_id)
    user_game_appointments = GameAppointmentEvent.get_future_games(user)
    cal = vobject.iCalendar()
    cal.add('method').value = 'PUBLISH' # IE/Outlook needs this
    for event in osr_events:
        vevent = cal.add('vevent')
        vevent.add('dtstart').value = event.start
        vevent.add('dtend').value = event.end
        vevent.add('summary').value = event.title
        vevent.add('uid').value = str(event.id)
    for event in user_game_appointments:
        vevent = cal.add('vevent')
        vevent.add('dtstart').value = event.start
        vevent.add('dtend').value = event.end
        vevent.add('summary').value = event.title
        vevent.add('uid').value = str(event.id)
    icalstream = cal.serialize()
    response = HttpResponse(icalstream, content_type='text/calendar')
    response['Filename'] = 'osr.ics' # IE needs this
    response['Content-Disposition'] = 'attachment; filename=osr.ics'
    return response
