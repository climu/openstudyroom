from django.contrib import admin
from .models import Tournament, Bracket, Match


mymodels = [Tournament, Bracket, Match]

admin.site.register(mymodels)
