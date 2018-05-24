from django.contrib import admin

# Register your models here.

from .models import Sgf, User, LeagueEvent, Division, LeaguePlayer,\
    Registry, Profile

#we create groups new_user, league_member and league_admin to help manage the league
#if not Group.objects.filter(name='new_user').exists():
#    group = Group.objects.create(name='new_user')

#if not Group.objects.filter(name='league_admin').exists():
#       group = Group.objects.create(name='league_admin')

#if not Group.objects.filter(name='league_member').exists():
 #      group = Group.objects.create(name='league_member')

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    search_fields = ['username']

mymodels = [
    Sgf,
    LeagueEvent,
    Division,
    LeaguePlayer,
    Registry,
    Profile,
]
admin.site.register(mymodels)
