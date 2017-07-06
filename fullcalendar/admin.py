from django.contrib import admin
from .models import PublicEvent, GameRequestEvent
# Register your models here.
mymodels = [PublicEvent, GameRequestEvent]

admin.site.register(mymodels)
