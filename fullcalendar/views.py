from django.shortcuts import render,get_object_or_404
from django.views.generic.edit import UpdateView,CreateView
from django.contrib.auth.decorators import user_passes_test,login_required
from django.http import Http404, HttpResponseRedirect,HttpResponse
from django.core.urlresolvers import reverse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from datetime import datetime
import json
from django.utils.timezone import make_aware
from league.models import is_league_admin, is_league_member
from .forms import UTCPublicEventForm
from .models import PublicEvent
from pytz import utc,timezone
#from django.utils import timezone
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
	initial = { 'start': datetime.now(),
				'end': datetime.now() }


	def test_func(self):
		return self.request.user.is_authenticated() and self.request.user.user_is_league_admin()

	def get_login_url(self):
		return '/'




def calendar_view(request):
	user = request.user
	return render(request, 'fullcalendar/calendar.html', { 'user':request.user,})

def json_feed(request):
	'''get all events for one user and serve a json'''
	user = request.user
	tz=request.user.get_timezone()
#	if user.is_authenticated():
	#	me_available_events = CalEvent.objects.filter(type='available',users = user)
	#	divisions = user.get_open_divisions()

	public_events = PublicEvent.objects.all()
	data = []
	for event in public_events:
		dict={
		'id' : event.pk,
		'title' : event.title,
		'start' : event.start.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
		'end' : event.end.astimezone(tz).strftime('%Y-%m-%d  %H:%M:%S'),
		'is_new': False,
		'editable': False,
		}
		if event.url:
			dict['url'] = event.url
		data.append(dict)
	return HttpResponse(json.dumps(data), content_type = "application/json")




@login_required()
@user_passes_test(is_league_member,login_url="/",redirect_field_name = None)
def save(request):
	'''get events modification from calendar ajax post'''
	tz=request.user.get_timezone()
	if request.method == 'POST':
		changed_events = json.loads(request.POST.get('events'));
		for event in changed_events:
			start = datetime.strptime(event['start'],'%Y-%m-%dT%H:%M:%S')
			start= make_aware(start,tz)
			end = datetime.strptime(event['end'],'%Y-%m-%dT%H:%M:%S')
			end= make_aware(end,tz)
			if event['is_new']:#we create a new event on server
				#if event['type'] == 'me-available':


				return HttpResponse('success')


@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def admin_cal_event_list(request):
	public_events = PublicEvent.objects.all()
	return render(request, 'fullcalendar/admin_cal_event_list.html', { 'public_events': public_events,})

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def admin_delete_event(request,pk):
	if request.method == 'POST':
		event = get_object_or_404(pk=pk)
		event.delete()
	else:
		raise Http404("What are you doing here ?")
	return HttpResponseRedirect(reverse('calendar:admin_cal_event_list'))
