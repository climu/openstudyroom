import json
from datetime import datetime, timedelta

import vobject
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template import loader
from django.utils import timezone
from django.utils.timezone import make_aware
from django.views.decorators.http import require_POST
from django.views.generic.edit import CreateView, UpdateView
from postman.api import pm_write
from pytz import utc

from community.models import Community
from league.forms import ActionForm
from league.models import Division, LeagueEvent, User

from .forms import CategoryForm, UTCPublicEventForm
from .models import AvailableEvent, Category, GameAppointmentEvent, GameRequestEvent, PublicEvent


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
        user_communities = user.groups.filter(name__endswith='community_member')
        communities = Community.objects.filter(
            Q(private=False) | Q(user_group__in=user_communities))

        # Get all public leagues and those the user is member of
        user_divisions = user.get_active_divisions()
        leagues = active_leagues.filter(
            Q(is_public=True) | Q(division__in=user_divisions)).distinct()

        context['user'] = user
        context['user_divisions'] = user_divisions
        context['user_opponents'] = calendar_data['user']['opponents']

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

    return render(request, 'fullcalendar/calendar_main_view.html', context)

def get_public_events(request):
    """
    Returns all public events inside a range period.
    If you may ask, community filtering now occurs
    in client side.
    """
    user = request.user
    tz = user.get_timezone() if user.is_authenticated else utc
    end = parseFCalendarDate(request.GET.get('end'), tz)
    start = parseFCalendarDate(request.GET.get('start'), tz)
    events = PublicEvent.get_formated(start, end, tz)
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

@require_POST
@login_required()
@user_passes_test(User.is_league_member, login_url='/', redirect_field_name=None)
def update_time_range_ajax(request):
    start = request.POST.get('start')
    end = request.POST.get('end')
    request.user.profile.start_cal = start
    request.user.profile.end_cal = end
    request.user.profile.save()
    return HttpResponse('success')


@require_POST
@login_required()
@user_passes_test(User.is_league_member, login_url='/', redirect_field_name=None)
def cancel_game_appointment_ajax(request):  # pylint: disable=inconsistent-return-statements
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
            'date': game_appointment.start,
        }
        message = plaintext.render(context)
        pm_write(
            sender=user,
            recipient=opponent,
            subject=subject,
            body=message,
            skip_notification=False,
        )
        return HttpResponse('success')
    return HttpResponseForbidden()


@require_POST
@login_required()
@user_passes_test(User.is_league_member, login_url='/', redirect_field_name=None)
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
@user_passes_test(User.is_league_member, login_url='/', redirect_field_name=None)
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
@user_passes_test(User.is_league_member, login_url='/', redirect_field_name=None)
def cancel_game_request_ajax(request):
    """Cancel a game request from calendar ajax post."""
    user = request.user
    pk = int(request.POST.get('pk'))
    game_request = get_object_or_404(GameRequestEvent, pk=pk, sender=user)
    game_request.delete()
    return HttpResponse('success')

@require_POST
@login_required()
@user_passes_test(User.is_league_member, login_url='/', redirect_field_name=None)
def create_game_ajax(request):
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

@login_required()
@user_passes_test(User.is_osr_admin, login_url='/', redirect_field_name=None)
def admin_cal_event_list(request):
    public_events = PublicEvent.objects.filter(community=None).order_by('-end')
    categories = Category.objects.filter(community=None)
    return render(
        request,
        'fullcalendar/admin_cal_event_list.html',
        {'public_events': public_events, 'categories': categories},
    )

@login_required()
@user_passes_test(User.is_league_member, login_url='/', redirect_field_name=None)
def admin_delete_category(request, pk):
    if request.method == 'POST':
        event = get_object_or_404(Category, pk=pk)
        form = ActionForm(request.POST)
        if form.is_valid() and event.can_edit(request.user):
            url = event.get_redirect_url()
            event.delete()
            return HttpResponseRedirect(url)
    raise Http404('What are you doing here ?')

@login_required()
@user_passes_test(User.is_league_member, login_url='/', redirect_field_name=None)
def admin_delete_event(request, pk):
    if request.method == 'POST':
        event = get_object_or_404(PublicEvent, pk=pk)
        form = ActionForm(request.POST)
        if form.is_valid() and event.can_edit(request.user):
            url = event.get_redirect_url()
            event.delete()
            return HttpResponseRedirect(url)
    raise Http404('What are you doing here ?')

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
