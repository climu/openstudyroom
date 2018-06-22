from datetime import datetime
import json
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import loader
from django.shortcuts import get_object_or_404
from django.db.models.functions import Lower
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic.edit import CreateView, UpdateView
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.utils import timezone
from league.models import User, Sgf
from league.forms import SgfAdminForm, ActionForm
from fullcalendar.forms import UTCPublicEventForm
from community.forms import CommunytyUserForm
from pytz import utc
from .models import Tournament, Bracket, Match, TournamentPlayer, TournamentGroup, Round, TournamentEvent
from .forms import TournamentForm, TournamentGroupForm, RoundForm, TournamentAboutForm,\
    TournamentPlayerProfileForm, ForfeitForm
from .utils import save_round


def rules(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    admin = tournament.is_admin(request.user)
    groups = TournamentGroup.objects.filter(league_event=tournament).exists()

    context = {
        'tournament': tournament,
        'admin': admin,
        'groups': groups,
    }
    template = loader.get_template('tournament/rules.html')
    return HttpResponse(template.render(context, request))

def prizes(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    admin = tournament.is_admin(request.user)
    groups = TournamentGroup.objects.filter(league_event=tournament).exists()

    context = {
        'tournament': tournament,
        'admin': admin,
        'groups': groups,
    }
    template = loader.get_template('tournament/prizes.html')
    return HttpResponse(template.render(context, request))

def about(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    admin = tournament.is_admin(request.user)
    groups = TournamentGroup.objects.filter(league_event=tournament).exists()
    now = timezone.now()
    events = tournament.tournamentevent_set.filter(end__gte=now).order_by('start')

    context = {
        'tournament': tournament,
        'admin': admin,
        'groups': groups,
        'events': events
    }
    template = loader.get_template('tournament/about.html')
    return HttpResponse(template.render(context, request))

def brackets_view(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    groups = TournamentGroup.objects.filter(league_event=tournament).exists
    brackets = tournament.bracket_set.all()


    context = {
        'tournament': tournament,
        'groups': groups,
        'admin': tournament.is_admin(request.user),
        'brackets': brackets
    }
    template = loader.get_template('tournament/brackets.html')
    return HttpResponse(template.render(context, request))

def groups_view(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    groups = TournamentGroup.objects.filter(league_event=tournament).order_by('order')

    for group in groups:
        results = group.get_results()
        group.results = results
    context = {
        'tournament': tournament,
        'groups': groups,
        'admin': tournament.is_admin(request.user)

    }
    template = loader.get_template('tournament/groups.html')
    return HttpResponse(template.render(context, request))

def games_view(request, tournament_id, sgf_id=None):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    groups = TournamentGroup.objects.filter(league_event=tournament).exists()
    sgfs = tournament.sgf_set.only(
        'date',
        'black',
        'white',
        'winner',
        'result',
        'league_valid').filter(league_valid=True).\
        prefetch_related('white', 'black', 'winner').\
        select_related('white__profile', 'black__profile').\
        order_by('-date')
    context = {
        'sgfs': sgfs,
        'tournament': tournament,
        'groups': groups,
        'admin': tournament.is_admin(request.user)
    }
    if sgf_id is not None:
        sgf = get_object_or_404(Sgf, pk=sgf_id)
        context.update({'sgf':sgf})
    template = loader.get_template('tournament/games.html')
    return HttpResponse(template.render(context, request))

def players_view(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    groups = TournamentGroup.objects.filter(league_event=tournament).exists()
    players = tournament.leagueplayer_set.order_by(Lower('user__username'))
    context = {
        'tournament': tournament,
        'players': players,
        'groups': groups,
        'admin': tournament.is_admin(request.user)
    }
    template = loader.get_template('tournament/players.html')
    return HttpResponse(template.render(context, request))

def calendar(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    groups = TournamentGroup.objects.filter(league_event=tournament).exists

    context = {
        'tournament': tournament,
        'admin': tournament.is_admin(request.user),
        'groups': groups,
        'user': request.user
    }
    template = loader.get_template('tournament/calendar.html')
    return HttpResponse(template.render(context, request))

def calendar_feed(request, tournament_id):
    """get all events for one user and serve a json."""

    tournament = get_object_or_404(Tournament, pk=tournament_id)
    user = request.user
    # get user timezone
    if user.is_authenticated:
        tz = user.get_timezone()
    else:
        tz = utc

    # Get start and end from request and use user tz
    start = datetime.strptime(request.GET.get('start'), '%Y-%m-%d')
    start = timezone.make_aware(start, tz)
    end = datetime.strptime(request.GET.get('end'), '%Y-%m-%d')
    end = timezone.make_aware(end, tz)

    data = tournament.get_formated_events(start, end, tz)
    return HttpResponse(json.dumps(data), content_type="application/json")
############################################################################
###                  Admin views                                         ###
############################################################################

class TournamentCreate(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create a tournament"""
    form_class = TournamentForm
    model = Tournament
    template_name_suffix = '_create_form'
    initial = {
        'begin_time': datetime.now(),
        'end_time': datetime.now(),
        'ppwin': 1,
        'pploss': 0,
        'event_type': 'tournament',
        }

    def test_func(self):
        return self.request.user.is_authenticated() and \
            self.request.user.is_league_admin()

    def get_login_url(self):
        return '/'

class TournamentEventUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    form_class = UTCPublicEventForm
    model = TournamentEvent
    template_name_suffix = '_update_form'

    def test_func(self):
        return self.get_object().can_edit(self.request.user)

    def get_login_url(self):
        return '/'
    def get_success_url(self):
        return reverse(
            'tournament:manage_calendar',
            kwargs={'tournament_id': self.get_object().tournament.pk}
            )

@login_required()
def manage_calendar(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if not tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    groups = TournamentGroup.objects.filter(league_event=tournament).exists
    events = tournament.tournamentevent_set.all()
    context = {
        'tournament': tournament,
        'events': events,
        'groups': groups
    }
    template = loader.get_template('tournament/manage_events.html')
    return HttpResponse(template.render(context, request))

@login_required()
def create_calendar_event(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if not tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    if request.method == 'POST':
        form = UTCPublicEventForm(request.POST)
        if form.is_valid():
            event = TournamentEvent()
            event.start = form.cleaned_data['start']
            event.end = form.cleaned_data['end']
            event.description = form.cleaned_data['description']
            event.title = form.cleaned_data['title']
            event.url = form.cleaned_data['url']
            event.tournament = tournament
            event.save()
            message = "Succesfully created a tournament event."
            messages.success(request, message)
            return HttpResponseRedirect(reverse(
                'tournament:manage_calendar',
                kwargs={'tournament_id': tournament.pk}
            ))
    form = UTCPublicEventForm({
        'start': datetime.now(),
        'end': datetime.now()
    })
    context = {
        'tournament': tournament,
        'form': form
    }
    template = loader.get_template('tournament/create_calendar_event.html')
    return HttpResponse(template.render(context, request))

@login_required()
def edit_player_profile(request, tournament_id, user_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    user = get_object_or_404(User, pk=user_id)
    if not tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    groups = TournamentGroup.objects.filter(league_event=tournament).exists()

    if request.method == 'POST':
        form = TournamentPlayerProfileForm(request.POST, instance=user.profile)
        if form.is_valid():
            form.save()
            message = "Succesfully updated " + user.username + " profile."
            messages.success(request, message)
            return HttpResponseRedirect(reverse(
                'tournament:players',
                kwargs={'tournament_id': tournament.pk}
            ))
    form = TournamentPlayerProfileForm(instance=user.profile)
    context = {
        'tournament': tournament,
        'form': form,
        'groups': groups,
        'user': user
    }
    template = loader.get_template('tournament/edit_profile.html')
    return HttpResponse(template.render(context, request))

@login_required()
def edit_about(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if not tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    groups = TournamentGroup.objects.filter(league_event=tournament).exists()

    if request.method == "POST":
        form = TournamentAboutForm(request.POST, instance=tournament)
        if form.is_valid():
            tournament.description = form.cleaned_data['description']
            tournament.about = form.cleaned_data['about']
            tournament.save()
            message = "Succesfully updated the " + tournament.name + " description."
            messages.success(request, message)
            return HttpResponseRedirect(reverse(
                'tournament:about',
                kwargs={'tournament_id': tournament.pk}
            ))
    else:
        form = TournamentAboutForm(instance=tournament)
    context = {
        'tournament': tournament,
        'form': form,
        'groups': groups
    }
    template = loader.get_template('tournament/edit_about.html')
    return HttpResponse(template.render(context, request))

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
def manage_settings(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if not tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
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
def manage_groups(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if not tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
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
def create_bracket(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if not tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    if request.method == 'POST':
        bracket = Bracket(tournament=tournament)
        bracket.order = tournament.last_bracket_order() + 1
        bracket.save()
    return HttpResponseRedirect(reverse(
        'tournament:manage_brackets',
        kwargs={'tournament_id': tournament.pk}
    ))

@login_required()
def create_match(request, round_id):
    round = get_object_or_404(Round, pk=round_id)
    if not round.bracket.tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    if request.method == 'POST':
        round.create_match()

    return HttpResponseRedirect(reverse(
        'tournament:manage_brackets',
        kwargs={'tournament_id': round.bracket.tournament.pk}
    ))

@login_required()
def delete_match(request, round_id):
    """Delete the last match of a tournament"""
    round = get_object_or_404(Round, pk=round_id)
    if not round.bracket.tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    match = round.match_set.all().order_by('order').last()
    if match is not None:
        if match.player_1 or match.player_2:
            message = "Last match of " + round.name + " have players. Remove players before deleting the match "
            messages.success(request, message)
        elif request.method == 'POST':
            round.delete_match()
    return HttpResponseRedirect(reverse(
        'tournament:manage_brackets',
        kwargs={'tournament_id': round.bracket.tournament.pk}
    ))

@login_required()
def rename_round(request, round_id):
    round = get_object_or_404(Round, pk=round_id)
    if not round.bracket.tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    if request.method == 'POST':
        form = RoundForm(request.POST)
        if form.is_valid():
            round.name = form.cleaned_data['name']
            round.save()
    return HttpResponseRedirect(reverse(
        'tournament:manage_brackets',
        kwargs={'tournament_id': round.bracket.tournament.pk}
    ))


@login_required()
def create_round(request, bracket_id):
    bracket = get_object_or_404(Bracket, pk=bracket_id)
    if not bracket.tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    if request.method == 'POST':
        form = RoundForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            last_round = bracket.round_set.all().order_by('order').last()
            if last_round:
                order = bracket.round_set.all().order_by('order').last().order + 1
            else:
                order = 0
            round = Round.objects.create(bracket=bracket, order=order, name=name)
            Match.objects.create(bracket=bracket, round=round, order=0)
    return HttpResponseRedirect(reverse(
        'tournament:manage_brackets',
        kwargs={'tournament_id': bracket.tournament.pk}
    ))


@login_required()
def rename_bracket(request, bracket_id):
    bracket = get_object_or_404(Bracket, pk=bracket_id)
    if not bracket.tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    if request.method == 'POST':
        form = RoundForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            bracket.name = name
            bracket.save()
    return HttpResponseRedirect(reverse(
        'tournament:manage_brackets',
        kwargs={'tournament_id': bracket.tournament.pk}
    ))

@login_required()
def delete_bracket(request, bracket_id):
    bracket = get_object_or_404(Bracket, pk=bracket_id)
    if not bracket.tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    if request.method == 'POST':
        bracket.delete()
    return HttpResponseRedirect(reverse(
        'tournament:manage_brackets',
        kwargs={'tournament_id': bracket.tournament.pk}
    ))


@login_required()
def delete_round(request, round_id):
    round = get_object_or_404(Round, pk=round_id)
    if not round.bracket.tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    if request.method == 'POST':
        round.delete()
    return HttpResponseRedirect(reverse(
        'tournament:manage_brackets',
        kwargs={'tournament_id': round.bracket.tournament.pk}
    ))


@login_required()
def save_brackets(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if not tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    if request.method == 'POST':
        brackets = json.loads(request.POST.get('brackets'))
        for bracket_id, rounds in brackets.items():
            bracket = get_object_or_404(Bracket, pk=bracket_id, tournament=tournament)
            for round_id, matches in rounds.items():
                round = get_object_or_404(Round, pk=round_id, bracket=bracket)
                save_round(round, matches)

    return HttpResponse("success")


@login_required()
def manage_brackets(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if not tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    players = TournamentPlayer.objects.filter(event=tournament).order_by('order')
    brackets = tournament.bracket_set.all()
    if not brackets:
        Bracket.objects.create(tournament=tournament, order=0)
    if not brackets.first().match_set.all():
        brackets.first().generate_bracket()
    context = {
        'tournament': tournament,
        'players': players,
        'brackets': brackets,
    }
    groups = TournamentGroup.objects.filter(league_event=tournament).order_by('order')
    if groups is not None:
        # get the players that are not in any groups
        seeded_players = players.filter(division=None)
        for group in groups:
            results = group.get_results()
            group.results = results
        context.update({
            'seeded_players': seeded_players,
            'groups': groups
        })

    template = loader.get_template('tournament/manage_brackets.html')
    return HttpResponse(template.render(context, request))

@login_required()
def manage_games(request, tournament_id):
    """Manage tournament games."""
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if not tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    games = Sgf.objects.filter(events=tournament)
    if request.method == 'POST':
        pass
    context = {
        'tournament': tournament,
        'games': games
    }
    template = loader.get_template('tournament/manage_games.html')
    return HttpResponse(template.render(context, request))


@login_required()
def set_stage(request, tournament_id):
    """Set the stage of a tournament."""
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if not tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    if request.method == 'POST':
        form = ActionForm(request.POST)
        if form.is_valid():
            stage = form.cleaned_data['action']
            if int(stage) < 3:
                tournament.stage = stage
                tournament.save()
            return HttpResponseRedirect(form.cleaned_data['next'])
    raise Http404("What are you doing here ?")


@login_required()
def create_sgf(request, tournament_id):
    """Actually create a sgf db entry. Should be called after upload_sgf."""
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if not tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    if request.method == 'POST':
        form = SgfAdminForm(request.POST)
        if form.is_valid():
            sgf = Sgf()
            sgf.sgf_text = form.cleaned_data['sgf']
            sgf.p_status = 2
            sgf = sgf.parse()
            check = tournament.check_sgf_validity(sgf)
            if sgf.league_valid:
                sgf.save()
                sgf.update_related([tournament])
                if tournament.stage == 2 and check['match'] is not None:
                    match = check['match']
                    match.sgf = sgf
                    [bplayer, wplayer] = sgf.get_players(tournament)
                    bplayer = TournamentPlayer(pk=bplayer.pk)
                    wplayer = TournamentPlayer(pk=wplayer.pk)
                    if sgf.white == sgf.winner:
                        match.winner = wplayer
                    else:
                        match.winner = bplayer
                    match.save()
                message = " Succesfully created a SGF"
                messages.success(request, message)
            else:
                message = " the sgf didn't seems to pass the tests"
                messages.success(request, message)
    return HttpResponseRedirect(reverse(
        'tournament:manage_games',
        kwargs={'tournament_id': tournament.pk}
    ))

@login_required()
def upload_sgf(request, tournament_id):
    """THis view allow user to preview sgf with wgo along with valid status of the sgf.
        Can call save_sgf from it.
    """
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if not tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    if request.method == 'POST':
        form = SgfAdminForm(request.POST)
        if form.is_valid():
            sgf = Sgf()
            sgf.sgf_text = form.cleaned_data['sgf']
            sgf.p_status = 2
            sgf = sgf.parse()
            check = tournament.check_sgf_validity(sgf)
            form = SgfAdminForm(initial={'sgf': sgf.sgf_text})
            context = {
                'tournament': tournament,
                'sgf': sgf,
                'form': form,
                'match': check['match'],
                'group': check['group']
            }
            template = loader.get_template('tournament/upload_sgf.html')
            return HttpResponse(template.render(context, request))
    else:
        if 'sgf_data' in request.session:
            if request.session['sgf_data'] is None:
                raise Http404("What are you doing here ?")
            sgf = Sgf()
            sgf.sgf_text = request.session['sgf_data']
            request.session['sgf_data'] = None
            sgf.p_status = 2
            sgf = sgf.parse()
            check = tournament.check_sgf_validity(sgf)
            form = SgfAdminForm(initial={'sgf': sgf.sgf_text})
            context = {
                'tournament': tournament,
                'sgf': sgf,
                'form': form,
                'match': check['match'],
                'group': check['group']
            }
            template = loader.get_template('tournament/upload_sgf.html')
            return HttpResponse(template.render(context, request))
        else:
            raise Http404("What are you doing here ?")

@login_required()
def invite_user(request, tournament_id):
    """Invite a user in a tournament."""
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if not tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
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
def remove_players(request, tournament_id):
    """Remove a player from a tournament ajax powa"""
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if not tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    if request.method == "POST":
        players_list = json.loads(request.POST.get('players_list'))
        players = TournamentPlayer.objects.filter(pk__in=players_list)
        players.delete()
        return HttpResponse("success")
    else:
        raise Http404('what are you doing here ?')

@login_required()
def save_players_order(request, tournament_id):
    """Save the player order and remove players from ajax call"""
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if not tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
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
def create_group(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if not tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    if request.method == 'POST':
        form = TournamentGroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.league_event = tournament
            group.order = tournament.last_division_order() + 1
            group.save()
        return HttpResponseRedirect(reverse('tournament:manage_groups', kwargs={'tournament_id': tournament_id}))
    else:
        raise Http404("What are you doing here ?")


@login_required()
def save_groups(request, tournament_id):
    """Save tournament groups players from ajax call."""
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if not tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
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

@login_required
@user_passes_test(User.is_osr_admin, login_url="/", redirect_field_name=None)
def set_winner(request, tournament_id):
    '''set the winner for a division'''
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if request.method == 'POST':
        form = ActionForm(request.POST)
        if form.is_valid():
            user_id = form.cleaned_data['user_id']
            if user_id < 0:
                tournament.winner = None
            else:
                user = get_object_or_404(User, pk=user_id)
                tournament.winner = user
            tournament.save()
            return HttpResponseRedirect(form.cleaned_data['next'])
    raise Http404("What are you doing here ?")

@login_required
def forfeit_group(request, tournament_id, group_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    group = get_object_or_404(TournamentGroup, pk=group_id)
    if not tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    if group.league_event.pk != tournament.pk:
        raise Http404('What are you doing here?')

    if request.method == 'POST':
        form = ForfeitForm(request.POST)
        if form.is_valid():
            winner = get_object_or_404(TournamentPlayer, pk=form.cleaned_data['winner'])
            looser = get_object_or_404(TournamentPlayer, pk=form.cleaned_data['looser'])
            sgf = Sgf()
            sgf.winner = winner.user
            sgf.black = winner.user
            sgf.white = looser.user
            sgf.result = "Forfeit"
            sgf.p_status = 0
            sgf.wplayer = looser.user.username
            sgf.bplayer = winner.user.username
            sgf.league_valid = True
            sgf.save()
            sgf.events.add(tournament)
            sgf.divisions.add(group)

            return HttpResponseRedirect(form.cleaned_data['next'])

@login_required
def forfeit_bracket(request, tournament_id, match_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    match = get_object_or_404(Match, pk=match_id)
    if not tournament.is_admin(request.user):
        raise Http404('What are you doing here?')
    if match.bracket.tournament != tournament:
        raise Http404('What are you doing here?')

    if request.method == 'POST':
        form = ForfeitForm(request.POST)
        if form.is_valid():
            winner = get_object_or_404(TournamentPlayer, pk=form.cleaned_data['winner'])
            match.winner = winner
            match.save()
            return HttpResponseRedirect(form.cleaned_data['next'])
