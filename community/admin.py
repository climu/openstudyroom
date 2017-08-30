from django.contrib import admin
from .models import Community, CommunityLeague
# Register your models here.
mymodels = [Community, CommunityLeague]

admin.site.register(mymodels)
