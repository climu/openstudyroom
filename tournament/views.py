from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.contrib.auth.decorators import user_passes_test
from django.template import loader
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic.edit import CreateView, UpdateView
from django.contrib.auth.decorators import user_passes_test, login_required
import datetime
from community.forms import CommunytyUserForm
from .models import Tournament, Bracket, Match, TournamentPlayer, TournamentGroup
from .forms import TournamentForm, TournamentGroupForm
from django.contrib import messages
from django.core.urlresolvers import reverse
from league.models import User
import json

class TournamentCreate(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create a tournament"""
    form_class = TournamentForm
    model = Tournament
    template_name_suffix = '_create_form'
    initial = {'begin_time': datetime.datetime.now(),
               'end_time': datetime.datetime.now()}

    def test_func(self):
        return self.request.user.is_authenticated() and \
            self.request.user.is_league_admin()

    def get_login_url(self):
        return '/'

@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def tournament_list(request):
    tournaments = Tournament.objects.all()
    context = {
        'tournaments': tournaments,
    }
    template = loader.get_template('tournament/tournament_list.html')
    return HttpResponse(template.render(context, request))


@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def tournament_manage_settings(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    players = TournamentPlayer.objects.filter(event=tournament).order_by('order')
    form = TournamentForm(instance=tournament)
    context = {
        'tournament': tournament,
        'players': players,
        'form': form,
    }
    template = loader.get_template('tournament/manage_settings.html')
    return HttpResponse(template.render(context, request))

@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def tournament_manage_groups(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    players = TournamentPlayer.objects.filter(event=tournament).order_by('order')
    groups = TournamentGroup.objects.filter(league_event=tournament).order_by('order')
    context = {
        'tournament': tournament,
        'players': players,
        'groups': groups
    }
    template = loader.get_template('tournament/manage_groups.html')
    return HttpResponse(template.render(context, request))

@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def tournament_invite_user(request, tournament_id):
    """Invite a user in a tournament."""
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if request.method == 'POST':
        form = CommunytyUserForm(request.POST)
        if form.is_valid():
            user = User.objects.get(username__iexact=form.cleaned_data['username'])
            if TournamentPlayer.objects.filter(
                event=tournament,
                user=user
            ).exists():
                message = {{user.username}} + " is already in the tournament."
                messages.success(request, message)
                return HttpResponseRedirect(reverse(
                    'tournament:tournament_manage_settings',
                    kwargs={'tournament_id': tournament.pk}
                ))

            player = TournamentPlayer()
            player.event = tournament
            player.kgs_username = user.profile.kgs_username
            player.ogs_username = user.profile.ogs_username
            player.user = user
            player.order = tournament.last_player_order() + 1
            player.save()
            message = user.username + " is now a playing in this tournament."
            messages.success(request, message)
        else:
            message = "We don't have such a user."
            messages.success(request, message)
        return HttpResponseRedirect(reverse(
            'tournament:tournament_manage_settings',
            kwargs={'tournament_id': tournament.pk}
        ))

@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def tournament_remove_player(request, tournament_id, player_id):
    """Remove a player from a tournament"""
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    player = get_object_or_404(TournamentPlayer, pk=player_id)
    if request.method == "POST":
        player.delete()
        message = player.user.username + " is no longer in " + tournament.name + " tournament."
        messages.success(request, message)
        return HttpResponseRedirect(reverse(
            'tournament:tournament_manage_settings',
            kwargs={'tournament_id': tournament.pk}
        ))
    else:
        raise Http404('what are you doing here ?')

@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def save_players_order(request, tournament_id):
    """Save the player order and remove players from ajax call"""
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if request.method == 'POST':
        players_list = json.loads(request.POST.get('players_list'))
        removed_players = json.loads(request.POST.get('removed_players'))
        # Let's removed some players:
        if removed_players:
            for id in removed_players:
                player = get_object_or_404(TournamentPlayer, pk=id)
                player.delete()

        # Now we update the players order
        for order, id in enumerate(players_list):
            player = get_object_or_404(TournamentPlayer, pk=id)
            player.order = order
            player.save()

        return HttpResponse("success")
    else:
        raise Http404('what are you doing here ?')


@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def create_group(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if request.method == 'POST':
        form = TournamentGroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.league_event = tournament
            group.order = tournament.last_division_order() + 1
            group.save()
        return HttpResponseRedirect(reverse('tournament:manage_tournament', kwargs={'tournament_id': tournament_id}))
    else:
        raise Http404("What are you doing here ?")


@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def save_groups(request, tournament_id):
    """Save tournament groups players from ajax call."""
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if request.method == 'POST':
        # first we null all players division
        players = TournamentPlayer.objects.filter(event=tournament)
        players.update(division=None)
        groups = json.loads(request.POST.get('groups'))
        for group_id, players in groups.items():
            group = get_object_or_404(TournamentGroup, pk=group_id)
            if group.league_event.pk != tournament.pk:
                raise Http404("What are you doing here ?")
            for player_id in players:
                player = get_object_or_404(TournamentPlayer, pk=player_id)
                player.division = group
                player.save()

        return HttpResponse("success")
    else:
        raise Http404("What are you doing here ?")
