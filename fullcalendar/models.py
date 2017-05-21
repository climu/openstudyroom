from django.db import models
from django.utils import timezone
from django.db.models import Q

import datetime
import time
from league.models import User,Division

# Create your models here.

class CalEvent(models.Model):
	EVENT_TYPE_CHOICES = (
        ('public', 'public'),
        ('personal', 'personal'),
        ('division', 'division'),
        )
	begin_time = models.DateTimeField()
	end_time =  models.DateTimeField()
	title = models.CharField(max_length=20)
	description = models.TextField(blank=True)
	url = models.URLField(blank=True)
	type = models.CharField(# public, personal, division
		max_length=10,
		choices=EVENT_TYPE_CHOICES,
		default='public')
	users = models.ManyToManyField(User, blank=True) # games appointment are related to 2 users
	division = models.ManyToManyField(Division, blank=True) # availability to play is related to a division

	@staticmethod
	def get_cal_events(user):
		'''return a query of all event related to a user.'''
		if user.is_authenticated and user.user_is_league_member:
			divisions = user.get_open_divisions()
			cal_events = CalEvent.objects.filter(Q(type= 'public')|Q(type = 'personal',users = user)|Q(type = 'division',division__in = divisions))
			#personal_events = CalEvent.objects.filter(type = 'personal',users = user)
			#division_events = CalEvent.objects.filter(type ='division,' division = divisions )
		else :
			cal_events = CalEvent.objects.filter(type= 'public')
		return cal_events

	@staticmethod
	def get_future_cal_events(user):
		'''return a query of all future event related to a user.'''
		now = timezone.now()
		if user.is_authenticated and user.user_is_league_member:
			divisions = user.get_open_divisions()
			cal_events = CalEvent.objects.filter(end_time__gte = now).filter(Q(type= 'public')|Q(type = 'personal',users = user)|Q(type = 'division',division__in = divisions))
			#personal_events = CalEvent.objects.filter(type = 'personal',users = user)
			#division_events = CalEvent.objects.filter(type ='division,' division = divisions )
		else :
			cal_events = CalEvent.objects.filter(type= 'public').filter(end_time__gte = now)
		return cal_events
