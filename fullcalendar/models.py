from django.db import models
from django.utils import timezone
from django.db.models import Q

import datetime
import time
from league.models import User, Division

# Create your models here.


class CalEvent(models.Model):

    start = models.DateTimeField()
    end = models.DateTimeField()

    class Meta:
        abstract = True


class PublicEvent(CalEvent):
    title = models.CharField(max_length=30)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True)

    @staticmethod
    def get_future_public_events():
        '''return a query of all future public events to a user.'''
        now = timezone.now()
        public_events = PublicEvent.objects.filter(end__gte=now)
        return public_events


class AvailableEvent(CalEvent):
    user = models.ForeignKey(User)


class GameRequestEvent(CalEvent):
    sender = models.ForeignKey(User, related_name="%(app_label)s_%(class)s_related_sender",
                               related_query_name="%(app_label)s_%(class)ss_sender",)
    receivers = models.ManyToManyField(User, related_name="%(app_label)s_%(class)s_related_receiver",
                                       related_query_name="%(app_label)s_%(class)ss_receiver",)


class GameAppointmentEvent(CalEvent):
    users = models.ManyToManyField(User, related_name="%(app_label)s_%(class)s_related",
                                   related_query_name="%(app_label)s_%(class)ss",)
