from django.contrib import admin

from .models import GameAppointmentEvent, GameRequestEvent, PublicEvent

# Register your models here.
mymodels = [PublicEvent, GameRequestEvent, GameAppointmentEvent]

admin.site.register(mymodels)
