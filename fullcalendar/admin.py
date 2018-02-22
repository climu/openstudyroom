from django.contrib import admin
from .models import PublicEvent, GameRequestEvent, GameAppointmentEvent
# Register your models here.
mymodels = [PublicEvent, GameRequestEvent, GameAppointmentEvent]

admin.site.register(mymodels)
