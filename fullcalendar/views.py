from django.shortcuts import render, get_object_or_404
from django.views.generic.edit import UpdateView, CreateView
from django.contrib.auth.decorators import user_passes_test, login_required
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from datetime import datetime
import json
from django.utils.timezone import make_aware
from league.models import is_league_admin, is_league_member
from .forms import UTCPublicEventForm
from .models import PublicEvent, AvailableEvent
from pytz import utc, timezone
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
    return render(request, 'fullcalendar/calendar.html', {'user': request.user, })


def json_feed(request):
    '''get all events for one user and serve a json'''
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
        # 1st we get his availability
        me_available_events = AvailableEvent.objects.filter(user=user)
        for event in me_available_events:
            dict = {
                'id': 'me-a:' + str(event.pk),
                'title': 'I am available',
                'start': event.start.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                'end': event.end.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                'is_new': False,
                'editable': True,
                'type': 'me-available',
                'color': '#01DF3A',
                'className': 'me-available',
            }
            data.append(dict)
        # then we get opponents availability
        opponents = user.get_opponents()
        opponents_available_events = AvailableEvent.objects.filter(user__in=opponents)
        
    return HttpResponse(json.dumps(data), content_type="application/json")


@login_required()
@user_passes_test(is_league_member, login_url="/", redirect_field_name=None)
def save(request):
    """Get events modification from calendar ajax post.
    Right now it's disabled. It's working but since we can't display such events
    No need to invite users to use that for now.
    """
    user = request.user
    tz = user.get_timezone()
    if request.method == 'POST':
        # todo: add proper form to check crfs
        changed_events = ''
        changed_events = json.loads(request.POST.get('events'))
        for event in changed_events:
            if event['type'] == 'deleted':  # we deleted an event
                # event pk is stored in event title type:pk
                a = event['title'].find(':')
                pk = event['title'][a + 1:]
                if event['title'].startswith('me-a'):
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
                a = event['id'].find(':')
                pk = event['id'][a + 1:]
                if event['id'].startswith('me-a'):
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
