from django.shortcuts import render,get_object_or_404
from django.views.generic.edit import UpdateView,CreateView
from django.contrib.auth.decorators import user_passes_test,login_required
from django.http import Http404, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
import datetime
from league.models import is_league_admin
from .forms import UTCCalEventForm
from .models import CalEvent
# Create your views here.



class CalEventUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
	form_class = UTCCalEventForm
	model = CalEvent
	template_name_suffix = '_update_form'

	def test_func(self):
		return self.request.user.is_authenticated() and self.request.user.user_is_league_admin()

	def get_login_url(self):
		return '/'


class CalEventCreate(LoginRequiredMixin, UserPassesTestMixin, CreateView):
	form_class = UTCCalEventForm
	model = CalEvent
	template_name_suffix = '_create_form'
	initial = { 'begin_time': datetime.datetime.now(),
				'end_time': datetime.datetime.now() }


	def test_func(self):
		return self.request.user.is_authenticated() and self.request.user.user_is_league_admin()

	def get_login_url(self):
		return '/'




def calendar_view(request):
	cal_events = CalEvent.get_cal_events(request.user)
	return render(request, 'fullcalendar/calendar.html', { 'cal_events': cal_events,})


@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def admin_cal_event_list(request):
	public_events = CalEvent.objects.filter(type='public')
	return render(request, 'fullcalendar/admin_cal_event_list.html', { 'public_events': public_events,})

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def admin_delete_event(request,pk):
	if request.method == 'POST':
		event = get_object_or_404(CalEvent,pk=pk)
		event.delete()
	else:
		raise Http404("What are you doing here ?")
	return HttpResponseRedirect(reverse('calendar:admin_cal_event_list'))
