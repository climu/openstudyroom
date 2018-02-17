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

def tournament_view(request,tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    players = TournamentPlayer.objects.filter(event=tournament).order_by('order')
    groups = TournamentGroup.objects.filter(league_event=tournament).order_by('order')
    brackets = tournament.bracket_set.all()

    for group in groups:
        results = group.get_results()
        group.results = results
    context = {
        'tournament': tournament,
        'players': players,
        'groups': groups,
        'brackets': brackets
    }
    template = loader.get_template('tournament/tournament_view.html')
    return HttpResponse(template.render(context, request))
############################################################################
###                  Admin views                                         ###
############################################################################

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
def manage_settings(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)

    if request.method == 'POST':
        form = TournamentForm(request.POST, instance=tournament)
        if form.is_valid:
            form.save()

    form = TournamentForm(instance=tournament)

    players = TournamentPlayer.objects.filter(event=tournament).order_by('order')
    context = {
        'tournament': tournament,
        'players': players,
        'form': form,
    }
    template = loader.get_template('tournament/manage_settings.html')
    return HttpResponse(template.render(context, request))

@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def manage_groups(request, tournament_id):
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
def create_bracket(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if request.method == 'POST':
        bracket = Bracket(tournament=tournament)
        bracket.order = tournament.last_bracket_order() + 1
        bracket.save()
    return HttpResponseRedirect(reverse(
        'tournament:manage_brackets',
        kwargs={'tournament_id': tournament.pk}
    ))

@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def create_match(request, round_id):
    round = get_object_or_404(Bracket, pk=round_id)
    if request.method == 'POST':
        round.create_match()

    return HttpResponseRedirect(reverse(
        'tournament:manage_brackets',
        kwargs={'tournament_id': bracket.tournament.pk}
    ))

@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def manage_brackets(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    players = TournamentPlayer.objects.filter(event=tournament).order_by('order')
    brackets = tournament.bracket_set.all()
    if not brackets:
        Bracket.objects.create(tournament=tournament, order=0)
    if not brackets.first().match_set.all():
        brackets.first().generate_bracket()
    groups = TournamentGroup.objects.filter(league_event=tournament).order_by('order')
    for group in groups:
        results = group.get_results()
        group.results = results

    context = {
        'tournament': tournament,
        'players': players,
        'groups': groups,
        'brackets': brackets
    }
    template = loader.get_template('tournament/manage_brackets.html')
    return HttpResponse(template.render(context, request))

@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def invite_user(request, tournament_id):
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
                message = user.username + " is already in the tournament."
                messages.success(request, message)
                return HttpResponseRedirect(reverse(
                    'tournament:manage_settings',
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
            'tournament:manage_settings',
            kwargs={'tournament_id': tournament.pk}
        ))

@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def remove_players(request, tournament_id):
    """Remove a player from a tournament ajax powa"""
    if request.method == "POST":
        tournament = get_object_or_404(Tournament, pk=tournament_id)
        players_list = json.loads(request.POST.get('players_list'))
        players = TournamentPlayer.objects.filter( pk__in=players_list)
        players.delete()
        return HttpResponse("success")
    else:
        raise Http404('what are you doing here ?')

@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def save_players_order(request, tournament_id):
    """Save the player order and remove players from ajax call"""
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if request.method == 'POST':
        players_list = json.loads(request.POST.get('players_list'))
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
        return HttpResponseRedirect(reverse('tournament:tournament_manage_groups', kwargs={'tournament_id': tournament_id}))
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
