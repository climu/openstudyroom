from django.contrib import admin

from .models import Bracket, Match, Tournament

mymodels = [Tournament, Bracket, Match]

admin.site.register(mymodels)
