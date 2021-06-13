import json
import datetime
import io
from collections import OrderedDict
from time import sleep
from zipfile import ZipFile

import pytz
import requests
from django.shortcuts import get_object_or_404, render
from django.template import loader
from django.template.defaultfilters import slugify
from django.conf import settings
from django.http import (
    HttpResponse,
    HttpResponseRedirect,
    Http404,
    JsonResponse,
)
from django.urls import reverse
from django.db.models import Count, Case, IntegerField, When, Q, Prefetch
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.mail import send_mail
from django.views.generic.edit import CreateView, UpdateView
from django.views.decorators.clickjacking import xframe_options_exempt
from django.template.defaultfilters import date as _date, time as _time
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.functions import TruncMonth
from django.views.decorators.http import require_POST
from machina.core.db.models import get_model
from postman.api import pm_write

from discord_bind.models import DiscordUser
from tournament.models import Tournament
from community.models import Community
from . import utils
from . import ogs
from .models import Sgf, LeaguePlayer, User, LeagueEvent, Division, Registry, \
    Profile
from .forms import SgfAdminForm, AddWontPlayForm, RemoveWontPlayForm, ActionForm,\
    LeaguePopulateForm, UploadFileForm, DivisionForm,\
    LeagueEventForm, EmailForm, TimezoneForm, ProfileForm
from .go_federations import format_ffg_tou

ForumProfile = get_model('forum_member', 'ForumProfile')
discord_url_file = "/etc/discord_url.txt"

def scraper():
    """Check kgs to update our db.
    This is called every 5 mins by cron in production.
    - 1: check time since get from kgs
    - 2: Check which players are online on kgs and update db.
    - 3: wait 5 sec
    Do only one of the above actions
    - 4.1 look for some sgfs that analyse and maybe pulled as games
    - 4.2 check a player
    This is not a view. belongs in utils. Don't forget  to update cronjob tho.
    """


    # 1 check time since get from kgs
    now = timezone.now()
    last_kgs = Registry.get_time_kgs()
    delta = now - last_kgs
    delta_sec = delta.total_seconds()
    kgs_delay = Registry.get_kgs_delay()
    if delta_sec < kgs_delay:  # we can't scrape yet
        out = 'too soon'
        return out
    # 2 Check which players are online and update db
    # First KGS
    r = utils.kgs_connect()
    for m in json.loads(r.text)['messages']:
        if m['type'] == 'ROOM_JOIN' and m['channelId'] == 3627409:
            for kgs_user in m['users']:
                profile = Profile.objects.filter(kgs_username__iexact=kgs_user['name']).first()
                if profile is not None:
                    profile.last_kgs_online = now
                    if 'rank' in kgs_user:
                        profile.kgs_rank = kgs_user['rank'] # scraping the rank of the players
                    profile.save()
    # then OGS
    ogs_users = ogs.get_online_users()
    for ogs_user in ogs_users:
        profile = Profile.objects.filter(ogs_id=ogs_user['id']).first()
        if profile is not None:
            profile.ogs_rank = ogs.rating2rank(ogs_user['ratings']["overall"]["rating"])
            profile.last_ogs_online = now
            profile.save()
    #finally discord
    #first we set everyone to offline
    DiscordUser.objects.all().update(status='offline')
    discord_json = requests.get('https://discordapp.com/api/guilds/287487891003932672/widget.json', timeout=10).json()
    Registry.set_discord_presence_count(discord_json['presence_count'])
    discord_users = discord_json['members']
    for user in discord_users:
        discord_user = DiscordUser.objects.filter(uid=user['id']).first()
        if discord_user is not None:
            discord_user.status = user['status']
            discord_user.save()
    # 3 wait a bit
    sleep(2)

    # 4.1 look for some sgfs that we analyse and maybe record as games
    sgf = Sgf.objects.filter(p_status=2).first()
    if sgf is None:
        sgf = Sgf.objects.filter(p_status=1).first()
    if sgf is not None:
        # parse the sgf datas to populate the rows -> KGS/OGS archive request
        sgf = sgf.parse()
        # if the sgf doesn't have a result (unfinished game) we just delete it
        # If the game was a OGS private game result will also be '?'. See models.sgf.parse
        if sgf.result == '?':
            sgf.delete()
        else:
            valid_events = sgf.check_validity()[0]
            sgf.update_related(valid_events)
            sgf.save()
            # I think we could deal with sgf already in db one day here:
            # Populate existing sgf urlto and delete new sgf
        out = sgf

    # 4.2 no games to scrap let's check a player
    else:
        events = LeagueEvent.objects.filter(is_open=True)
        profiles = Profile.objects.filter(user__leagueplayer__event__in=events) \
            .distinct().order_by('-p_status')
        # if everyone has been checked.
        if not profiles.filter(p_status__gt=0).exists():
            profiles.update(p_status=1)
        if profiles.filter(p_status=2).exists():
            user = profiles.filter(p_status=2)[0].user
            user.check_user()
            out = user
        else:
            user = profiles.filter(p_status=1)[0].user
            user.check_user()
        out = user
    Registry.set_time_kgs(now)
    return out


def scraper_view(request):
    """Call the scraper."""
    out = scraper()
    return HttpResponse(out)


@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def timezone_update(request):
    """Update the timezone of request.user."""
    user = request.user
    if request.method == 'POST':
        tz = request.POST.get('tz')
        if tz == '---------':
            tz = 'UTC'
        user.profile.timezone = tz
        user.profile.save()
        now = timezone.now().astimezone(pytz.timezone(tz))
        now = _date(now) + ' ' + _time(now)
        return HttpResponse(now)
    else:
        form = TimezoneForm(instance=user.profile)
        context = {'user': user, 'form': form}
        template = loader.get_template('league/timezone_update.html')
        return HttpResponse(template.render(context, request))


def download_sgf(request, sgf_id):
    """Download one sgf file."""
    sgf = get_object_or_404(Sgf, pk=sgf_id)
    response = HttpResponse(sgf.sgf_text, content_type='application/octet-stream')
    # for testing special characters slugify("Andre🍃")
    str = slugify(sgf.wplayer) + '-' + slugify(sgf.bplayer) + '-' + sgf.date.strftime('%m/%d/%Y') + ".sgf"
    response['Content-Disposition'] = 'attachment; filename=%s' % str
    return response


def download_all_sgf(request, user_id):

    user = get_object_or_404(User, pk=user_id)

    in_memory = io.BytesIO()
    zip = ZipFile(in_memory, "a")

    black_sgfs = user.black_sgf.get_queryset()
    white_sgfs = user.white_sgf.get_queryset()

    for sgf in white_sgfs.union(black_sgfs):

        current_name = slugify(sgf.wplayer) + '-' + slugify(sgf.bplayer) + '-' + sgf.date.strftime('%m-%d-%Y')
        counter = 1

        for name_in_zip in zip.namelist():
            if current_name in name_in_zip:
                counter += 1

        current_name += "-" + str(counter) + ".sgf"
        zip.writestr(current_name, sgf.sgf_text)

    for file in zip.filelist:
        file.create_system = 0

    zip.close()

    response = HttpResponse(content_type="application/x-zip-compressed")
    response["Content-Disposition"] = "attachment; filename=" + user.username + ".zip"

    in_memory.seek(0)
    response.write(in_memory.read())

    return response

def games_datatable_api(request):
    """
    Feed datatable with games infos as JSON.
    https://datatables.net/manual/server-side
    """
    league_id = request.GET.get('league')
    base_sgfs_queryset = Sgf.objects.exclude(winner__isnull=True)
    if league_id:
        league = get_object_or_404(LeagueEvent, pk=league_id)
        base_sgfs_queryset = base_sgfs_queryset.filter(events=league)
    sgfs = Sgf.fetch_and_get_context(base_sgfs_queryset)
    out = {
        'draw': int(request.GET.get('draw', 0)),
        'recordsTotal': len(sgfs),
        'data': sgfs,
    }
    return JsonResponse(out)


def list_games(request, event_id=None, sgf_id=None):
    """List all games and allow to show one with wgo."""
    open_events = LeagueEvent.get_events(request.user).filter(is_open=True)

    context = {'open_events': open_events}
    if sgf_id is not None:
        sgf = get_object_or_404(Sgf, pk=sgf_id, league_valid=True)
        context.update({'sgf': sgf})

    if event_id is None:
        template = loader.get_template('league/archives_games.html')

    else:
        event = get_object_or_404(LeagueEvent, pk=event_id)
        template = loader.get_template('league/games.html')
        context.update({
            'event': event,
            'can_join': event.can_join(request.user),
            'can_quit': event.can_quit(request.user)
        })
    return HttpResponse(template.render(context, request))

def division_results(request, event_id=None, division_id=None):
    """Show the results of a division."""
    open_events = LeagueEvent.get_events(request.user).filter(is_open=True)
    if event_id is None:
        event = Registry.get_primary_event()
    else:
        event = get_object_or_404(LeagueEvent, pk=event_id)
    if division_id is None:
        division = Division.objects.filter(league_event=event).first()
    else:
        division = get_object_or_404(Division, pk=division_id)
    can_join = event.can_join(request.user)
    can_quit = event.can_quit(request.user)
    if division is None:
        can_edit_division_infos = False
        results = None
    else:
        can_edit_division_infos = request.user.is_authenticated and request.user.is_in_division(division)
        results = division.get_results()
    if results is None:
        number_players = 0
    else:
        number_players = len(results)
    template = loader.get_template('league/results.html')
    context = {
        'event': event,
        'division': division,
        'results': results,
        'open_events': open_events,
        'can_edit_division_infos': can_edit_division_infos,
        'can_join': can_join,
        'number_players': number_players,
        'can_quit': can_quit,
        'admin': request.user.is_authenticated and request.user.is_league_admin(event)
    }
    return HttpResponse(template.render(context, request))

@xframe_options_exempt
def division_results_iframe(request, event_id=None, division_id=None):
    """Show the results of a division through an iframe."""
    if event_id is None:
        event = Registry.get_primary_event()
    else:
        event = get_object_or_404(LeagueEvent, pk=event_id)
    if division_id is None:
        division = Division.objects.filter(league_event=event).first()
    else:
        division = get_object_or_404(Division, pk=division_id)
    if division is None:
        results = None
    else:
        results = division.get_results()
    if results is None:
        number_players = 0
    else:
        number_players = len(results)
    template = loader.get_template('league/results_iframe.html')
    context = {
        'event': event,
        'division': division,
        'results': results,
        'number_players': number_players,
    }
    return HttpResponse(template.render(context, request))

def meijin(request):
    """A simple view that redirects to the last open meijin league."""
    league = LeagueEvent.objects.filter(
        event_type='meijin',
        is_open=True,
        community__isnull=True
    ).order_by('end_time').first()
    return HttpResponseRedirect(reverse(
        'league:results',
        kwargs={'event_id': league.pk})
    )


def ladder(request):
    """A simple view that redirects to the last open ladder league."""
    league = LeagueEvent.objects.filter(
        event_type='ladder',
        is_open=True,
        community__isnull=True
    ).order_by('end_time').first()
    return HttpResponseRedirect(reverse(
        'league:results',
        kwargs={'event_id': league.pk})
    )


def ddk(request):
    """A simple view that redirects to the last open ddk league."""
    league = LeagueEvent.objects.filter(
        event_type='ddk',
        is_open=True,
        community__isnull=True
    ).order_by('end_time').first()
    return HttpResponseRedirect(reverse(
        'league:results',
        kwargs={'event_id': league.pk})
    )

def dan(request):
    """A simple view that redirects to the last open dan league."""
    league = LeagueEvent.objects.filter(
        event_type='dan',
        is_open=True,
        community__isnull=True
    ).order_by('end_time').first()
    return HttpResponseRedirect(reverse(
        'league:results',
        kwargs={'event_id': league.pk})
    )

def ninenine(request):
    """A simple view that redirects to the last open 9x9 league."""
    league = LeagueEvent.objects.filter(
        event_type='league',
        is_open=True,
        community__isnull=True,
        board_size=9
    ).order_by('end_time').first()

    return HttpResponseRedirect(reverse(
        'league:results',
        kwargs={'event_id': league.pk})
    )

def archives(request):
    """Show a list of all leagues."""
    events = LeagueEvent.get_events(request.user).exclude(event_type='tournament')
    open_events = events.filter(is_open=True)

    context = {
        'events': events,
        'open_events': open_events,
    }
    template = loader.get_template('league/archive.html')
    return HttpResponse(template.render(context, request))


def infos(request, event_id=None, division_id=None, ):
    """Show infos of one league: rules..."""
    open_events = LeagueEvent.get_events(request.user).filter(is_open=True)
    if event_id is None:
        event = Registry.get_primary_event()
    else:
        event = get_object_or_404(LeagueEvent, pk=event_id)
    can_join = event.can_join(request.user)
    can_quit = event.can_quit(request.user)
    context = {
        'event': event,
        'open_events': open_events,
        'can_join': can_join,
        'can_quit': can_quit
    }
    template = loader.get_template('league/event.html')
    return HttpResponse(template.render(context, request))


def list_players(request, event_id=None, division_id=None):
    """List all player of a league with related stats. Allow to filter by division."""
    open_events = LeagueEvent.get_events(request.user).filter(is_open=True)
    can_join = False
    # if no event is provided, we show all the league members in archive template
    if event_id is None:
        users = User.objects.filter(groups__name='league_member').\
            prefetch_related(
                'leagueplayer_set',
                Prefetch(
                    'winner_sgf',
                    queryset=Sgf.objects.defer('sgf_text').all()
                ),
                Prefetch(
                    'black_sgf',
                    queryset=Sgf.objects.defer('sgf_text').exclude(winner__isnull=True)
                ),
                Prefetch(
                    'white_sgf',
                    queryset=Sgf.objects.defer('sgf_text').exclude(winner__isnull=True)
                ),
                'profile', 'discord_user')
        users = [user.get_stats for user in users]
        context = {
            'users': users,
            'open_events': open_events,
        }
        template = loader.get_template('league/archives_players.html')
    else:
        event = get_object_or_404(LeagueEvent, pk=event_id)
        can_join = event.can_join(request.user)
        can_quit = event.can_quit(request.user)
        # if no division is provided, we show all players from this event
        if division_id is None:
            divisions = event.division_set.all()
        else:
            division = get_object_or_404(Division, pk=division_id)
            divisions = [division]
        for division in divisions:
            division.results = division.get_results
        context = {
            'open_events': open_events,
            'event': event,
            'divisions': divisions,
            'can_join': can_join,
            'can_quit': can_quit
        }
        template = loader.get_template('league/players.html')
    return HttpResponse(template.render(context, request))


@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def join_event(request, event_id, user_id):
    """Add a user to a league. After some check we calls the models.LeagueEvent.join_event method.

    We will also join all primary leagues as follow:
        - if we are joining a community league, we join all primary league of this community.
        - if not, we join all primary OSR leagues
    """

    # We already know that request.user is a league member.
    # So he can join an open event by himself.
    # If he is a league admin, he can make another user
    # If he isn't any of this just don't consider the request
    user = get_object_or_404(User, pk=user_id)
    if not request.user.is_league_admin and not request.user == user:
        message = "What are you doing here?"
        messages.success(request, message)
        return HttpResponseRedirect('/')

    event = get_object_or_404(LeagueEvent, pk=event_id)
    # No one should join a close event
    if not event.is_open:
        message = "You can't join a close event !"
        messages.success(request, message)
        return HttpResponseRedirect(reverse('league:league_account'))

    # Process request
    if request.method == 'POST':
        form = ActionForm(request.POST)
        if form.is_valid() and form.cleaned_data['action'] == 'join':
            # get primary leagues to auto join.
            if event.community is None:
                primary_leagues = LeagueEvent.objects.filter(
                    is_open=True,
                    community__isnull=True,
                    is_primary=True)
            else:
                primary_leagues = LeagueEvent.objects.filter(
                    is_open=True,
                    community=event.community,
                    is_primary=True)

            # set up success message
            message = "Welcome in " + event.name + " ! You can start playing right now.\n"


            if not user.join_event(event):
                message = "Oops ! Something went wrong. You didn't join."
                messages.success(request, message)
                return HttpResponseRedirect(form.cleaned_data['next'])

            joined_leagues = []
            for league in primary_leagues:
                if user.join_event(league):
                    joined_leagues.append(league)
            if joined_leagues:
                message += "On top of that, you automatically joined the following leagues: "
                for league in joined_leagues:
                    message += league.name + " "

            messages.success(request, message)
            return HttpResponseRedirect(form.cleaned_data['next'])

    # Default return
    return HttpResponseRedirect('/')


@require_POST
@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def quit_league(request, event_id, user_id=None):  # pylint: disable=inconsistent-return-statements
    """Allow a user to quit a league if he didn't play a game in it yet."""
    form = ActionForm(request.POST)
    if form.is_valid():
        league = get_object_or_404(LeagueEvent, pk=event_id)
        if user_id is None:
            user = request.user
        else:
            user = get_object_or_404(User, pk=user_id)
        # member can quit for them but admins can quit anyone
        if not (user == request.user or request.user.is_league_admin()):
            raise Http404('What are you doing here?1')
        if league.can_quit(user):
            player = LeaguePlayer.objects.filter(user=user, event=league).first()
            message = "Succesfully deleted the player " + user.username +\
                " from " + league.name
            messages.success(request, message)
            player.delete()
            return HttpResponseRedirect(form.cleaned_data['next'])
        else:
            message = "A player canot quit a league once he have played games in it."
            messages.success(request, message)
            return HttpResponseRedirect(form.cleaned_data['next'])

def account_activity(request, user_name):
    """
    Show all user's related events
    (his game appointments and his shared game requests with request.user)
    """
    user = get_object_or_404(User, username=user_name)
    context = {}
    calendar_data = {}
    calendar_data['profil'] = user.format()
    if request.user.is_authenticated:
        calendar_data['user'] = request.user.format()
    context['calendar_data'] = calendar_data
    context['user'] = user
    return render(request, 'league/account_activity.html', context)

def account(request, user_name=None):
    """Show a user account.
    if url ask for a user( /league/user/climu) display that user profile.
    if none, we check if user is auth and, if so,  we display his own profile.
    """
    # if no user provide  by url, we check if user is auth and if so display hi own profile
    if user_name is None:
        if request.user.is_authenticated:
            user = request.user
        else:
            # maybe a view with a list of all our users might be cool redirection here
            return HttpResponseRedirect('/')
    else:
        user = get_object_or_404(User, username=user_name)
        # user = User.objects.get(username=user_name)
    context = {}

    if not user.is_league_member():
        return HttpResponseRedirect('/')

    if request.user.is_authenticated:
        num_total_games = user.white_sgf.filter(black=request.user).count()\
            + user.black_sgf.filter(white=request.user).count()
        user_lost_games = user.white_sgf.filter(winner=request.user).count()\
            + user.black_sgf.filter(winner=request.user).count()
        user_won_games = num_total_games - user_lost_games

        if num_total_games != 0:
            won_perc = user_lost_games / num_total_games * 100
            lost_perc = user_won_games / num_total_games * 100
        else:
            won_perc = -1
            lost_perc = -1

        sgfs_links_w = Sgf.objects.\
            exclude(winner__isnull=True).\
            filter(wplayer=user.username).\
            filter(bplayer=request.user.username)
        sgfs_links_b = Sgf.objects.\
            exclude(winner__isnull=True).\
            filter(bplayer=user.username).\
            filter(wplayer=request.user.username)
        sgfs_links = sgfs_links_b.union(sgfs_links_w)

        context.update({
            'user_won_games': user_won_games,
            'user_lost_games': user_lost_games,
            'sgfs_links': sgfs_links,
            'won_perc': won_perc,
            'lost_perc': lost_perc,
        })

    open_events = LeagueEvent.get_events(request.user)\
        .filter(is_open=True)\
        .exclude(event_type='tournament')

    discord_user = DiscordUser.objects.filter(user=user).first()

    players = user.leagueplayer_set.exclude(event__event_type='tournament').order_by('-pk')

    sgfs = Sgf.objects.defer('sgf_text').\
        exclude(date__isnull=True).\
        exclude(winner__isnull=True).\
        filter(Q(white=user) | Q(black=user)).\
        select_related("white", "white__profile", "black", "black__profile", "winner").\
        prefetch_related("white__discord_user", "black__discord_user")

    for event in open_events:
        event_players = LeaguePlayer.objects.filter(user=user, event=event)
        if len(event_players) > 0:
            event.is_in = True
            player = event_players.first()
            event.this_player = player
            results = player.division.get_results()
            event.results = results
        else:
            event.is_in = False

    won_divisions = user.won_division.get_queryset().order_by('-league_event__end_time')
    won_tournaments = user.won_tournament.get_queryset().order_by('-end_time')

    games_stats = sgfs\
        .annotate(month=TruncMonth('date'))\
        .values('month')\
        .annotate(games=Count('id', distinct=True))\
        .annotate(wins=Count(
            Case(
                When(winner=user, then=1),
                output_field=IntegerField(),
                distinct=True
            )))\
        .annotate(losses=Count(
            Case(
                When(~Q(winner=user), then=0),
                output_field=IntegerField(),
                distinct=True
            )))\
        .values('month', 'games', 'wins', 'losses')\
        .order_by('month')
    games_stats = list(games_stats)
    games_stats = json.dumps(games_stats, cls=DjangoJSONEncoder)
    if len(sgfs) == 0:
        sgfs = None
    context.update({
        'players': players,
        'open_events': open_events,
        'sgfs': sgfs,
        'user': user,
        'discord_user': discord_user,
        'won_divisions': won_divisions,
        'won_tournaments': won_tournaments,
        'games_stats': games_stats
    })
    template = loader.get_template('league/account.html')
    return HttpResponse(template.render(context, request))


def game_api(request, sgf_id, event_id=None):
    """Returns a json to be use in game pages. Json is formated as:
    'infos': players, date, league, group, permalink, download link.
    'sgf': sgf datas as plain text string
    """

    sgf = get_object_or_404(Sgf, pk=sgf_id)
    event = None
    if event_id is not None:
        event = get_object_or_404(LeagueEvent, pk=event_id)

    html = loader.render_to_string(
        "league/includes/game_info.html",
        {'sgf': sgf, 'event': event}
    )
    data = {}
    data['sgf'] = sgf.sgf_text.replace(';B[]', "").replace(';W[]', "").replace(';)', '').replace(':/', "").replace(';-)', '')
    data['permalink'] = '/league/games/' + str(sgf.pk) + '/'
    data['game_infos'] = html
    data['white'] = sgf.white.username
    data['black'] = sgf.black.username
    data['id'] = str(sgf.pk)

    return JsonResponse(data)


def scrap_list(request):
    open_events = LeagueEvent.get_events(request.user).filter(is_open=True)
    profiles = Profile.objects.filter(user__leagueplayer__event__in=open_events)\
        .distinct().order_by('-p_status')
    context = {
        'open_events': open_events,
        'profiles': profiles
    }
    return render(request, 'league/scrap_list.html', context)


@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def scrap_list_up(request, profile_id):
    """ Set user profile p_status to 2 so this user will be checked soon"""
    profile = get_object_or_404(Profile, pk=profile_id)
    if profile.p_status == 2:
        message = str(profile.user) + ' will already be scraped with hight priority'
        messages.success(request, message)
        return HttpResponseRedirect(reverse('league:scrap_list'))
    if profile.user == request.user or request.user.is_league_admin():
        if request.method == 'POST':
            form = ActionForm(request.POST)
            if form.is_valid():
                if form.cleaned_data['action'] == 'p_status_up':
                    profile.p_status = 2
                    profile.save()
                    message = 'You just moved ' + str(profile.user.username) + ' up the scrap list'
                    messages.success(request, message)
                    return HttpResponseRedirect(reverse('league:scrap_list'))
    raise Http404("What are you doing here ?")


def discord_api(request):
    """ API to feed the discord bot"""
    uids = request.GET.getlist('uids', '{}')
    discord_users = DiscordUser.objects.filter(uid__in=uids).select_related('user__profile')
    out = {}
    for u in discord_users:
        out[u.uid] = {
            'osr_username': u.user.username,
            'timezone': u.user.profile.timezone,
            'country': u.user.profile.country.name,
        }
        players = u.user.leagueplayer_set.all()
        leagues = LeagueEvent.objects.filter(leagueplayer__in=players, is_open=True)
        if leagues:
            out[u.uid].update({
                'leagues': [{"name": league.name, "id":league.pk} for league in leagues]
            })

        if u.user.profile.bio is not None:
            out[u.uid].update({'bio': u.user.profile.bio._get_raw()})
        if u.user.profile.kgs_username:
            out[u.uid].update({
                'kgs_username': u.user.profile.kgs_username,
                'kgs_rank': u.user.profile.kgs_rank,
            })
        if u.user.profile.ogs_id > 0:
            out[u.uid].update({
                'ogs_username': u.user.profile.ogs_username,
                'ogs_rank': u.user.profile.ogs_rank,
                'ogs_id': u.user.profile.ogs_id,
            })

    return JsonResponse(out)

#################################################################
####    ADMINS views    #########################################
#################################################################


@login_required()
@user_passes_test(User.is_osr_admin, login_url="/", redirect_field_name=None)
def admin(request):
    """Main admin view. Template will show:
        - admin board: embebed google doc.
        - list of new users. Ajax buttons to accept, delete or delete with message the users.
    """
    if request.method == 'POST':
        # Ajax actions to accept, delete or delete with message the new users.
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        user = User.objects.get(pk=user_id)
        if user.groups.filter(name='new_user').exists() and action == "welcome":
            # remove new user group
            group = Group.objects.get(name='new_user')
            group.user_set.remove(user)
            # add league_member group
            group = Group.objects.get(name='league_member')
            user.groups.add(group)
            # send email
            utils.quick_send_mail(user, 'emails/welcome.txt')

            # send discord webhook
            if settings.DEBUG:
                discord_url = 'http://exemple.com' # change this for local test
            else:
                with open('/etc/discord_welcome_hook_url.txt') as f:
                    discord_url = f.read().strip()
            n_users = User.objects.filter(groups__name__in=['league_member']).count()
            message = "Please welcome **%s** who is OSR member number %d with a violent game of baduk.\n"\
                % (user.username, n_users)
            if user.profile.kgs_username:
                message += "KGS : " + user.profile.kgs_username + " \n"
            if user.profile.ogs_username:
                message += "OGS : [" + user.profile.ogs_username +\
                    "](https://online-go.com/player/" + str(user.profile.ogs_id) + ")"
                if user.profile.ogs_rank:
                    message += " (" + user.profile.ogs_rank + ")"
            values = {"content": message}
            requests.post(discord_url, json=values)

            # manage communities welcome
            community_groups = user.groups.\
                filter(name__icontains='_community_new_member').\
                filter(new_user_community__close=False)
            for group in community_groups:
                user.groups.add(group.new_user_community.get().user_group)
                user.groups.remove(group)

        elif action[0:6] == "delete":
            if action[7:15] == "no_games":  # deletion due to no played games
                utils.quick_send_mail(user, 'emails/no_games.txt')
            if action[7:] == "email_confirm":
                utils.quick_send_mail(user, 'emails/email_confirm.txt')
            user.delete()
        else:
            return HttpResponse('failure')
        return HttpResponse('succes')

    # on normal /league/admin load
    else:
        # get new users
        new_users = User.objects.filter(groups__name='new_user')
        # get users without a profile
        no_profile_users = User.objects.filter(profile=None)

        # get url of admin board if debug = False
        if settings.DEBUG:
            board_url = 'https://mensuel.framapad.org/p/1N0qTQCsk6?showControls=true&showChat=false&showLineNumbers=false&useMonospaceFont=false'
        else:
            with open('/etc/admin_board_url.txt') as f:
                board_url = f.read().strip()
        context = {
            'new_users': new_users,
            'board_url': board_url,
            'no_profile_users': no_profile_users,
        }
        template = loader.get_template('league/admin/dashboard.html')
        return HttpResponse(template.render(context, request))


@require_POST
@login_required()
@user_passes_test(User.is_osr_admin, login_url="/", redirect_field_name=None)
def admin_set_meijin(request):
    """Set one user to be meijin. Calls user.set_meijin methods."""
    form = ActionForm(request.POST)
    if form.is_valid():
        user = get_object_or_404(User, pk=form.cleaned_data['user_id'])
        user.set_meijin()
        message = user.username + " is now the new Meijin !"
        messages.success(request, message)
    return HttpResponseRedirect(reverse('league:admin_users_list'))


@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def admin_sgf_list(request):
    """Show all sgf (valids or not) for admins."""
    sgfs = Sgf.objects.defer('sgf_text').all()
    context = {'sgfs': sgfs}
    return render(request, 'league/admin/sgf_list.html', context)


@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def user_leagues_manage(request, user_id):
    """Allows admins to manage users leagues using ajax request.
        Mind that quit_league and join_league are still here for users if the league is open
    """
    # first set up global vars
    user = get_object_or_404(User, pk=user_id)
    # on get we feed one user info
    if request.method == 'GET':
        leagues = LeagueEvent.objects.filter(is_open=True)
        # if community is provided, we filter community leagues only
        community_pk = request.GET.get('community', None)
        if community_pk is not None:
            community = Community.objects.get(pk=community_pk)
            leagues = leagues.filter(community=community)
        else:
            leagues = leagues.filter(community=None)
        leagues_list = []
        for league in leagues:
            divisions = league.division_set.all()
            player = LeaguePlayer.objects.filter(user=user, event=league).first()
            if player is not None:
                player_division = player.division
            else:
                player_division = None

            divisions_list = []
            for division in divisions:
                divisions_list.append({
                'pk': division.pk,
                'name': division.name,
                'is_in': division == player_division
                })

            leagues_list.append({
            'name': league.name,
            'pk': league.pk,
            'can_join': league.can_join(user, request.user),
            'can_quit': league.can_quit(user, request.user),
            'is_in': player_division is not None,
            'divisions': divisions_list
            })
        out = {
            'user_pk': user.pk,
            'username': user.username,
            'leagues': leagues_list
        }
        return JsonResponse(out)
    else: # POST
        leagues_list = request.POST.get('leaguesList')
        if leagues_list is not None:
            leagues_list = json.loads(leagues_list)
        #    [{ 'leagueId':... , 'divisionID': ...}, {...}, ...]
        for item in leagues_list:
            league = get_object_or_404(LeagueEvent, pk=item['leagueId'])
            # We check if request.user is league admin and don't touch league if not.

            if not request.user.is_league_admin(league):
                continue
            if item['divisionId'] != "0":
                division = league.division_set.filter(pk=item['divisionId']).first()
                if division is not None:
                    if league.assign(user, division, request.user):
                        HttpResponse('success')
            elif league.can_quit(user, request.user):
                player = LeaguePlayer.objects.filter(user=user, event=league).first()
                player.delete()

        return HttpResponse('success')





# Next 3 views handle sgf upload.
# Worklfow is: handle_upload_sgf -> upload_sgf -> create_sgf


@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def handle_upload_sgf(request, tournament_id=None):
    """Get sgf datas from an uploaded file and redctect to upload_sgf view.
        sgf datas are store in request.session. Maybe we could avoid that.
        create a form from it and loads the template should make it?
    """
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            sgf_data = file.read().decode('UTF-8')
            request.session['sgf_data'] = sgf_data
            if tournament_id is None:
                return HttpResponseRedirect(reverse('league:upload_sgf'))
            else:
                tournament = get_object_or_404(Tournament, pk=tournament_id)
                return HttpResponseRedirect(reverse('tournament:upload_sgf', args=[tournament.pk]))
        else:
            raise Http404("What are you doing here ?")
    else:
        raise Http404("What are you doing here ?")


@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def create_sgf(request):
    """Actually create a sgf db entry. Should be called after upload_sgf."""
    if request.method == 'POST':
        form = SgfAdminForm(request.POST)
        if form.is_valid():
            sgf = Sgf()
            sgf.sgf_text = form.cleaned_data['sgf']
            sgf.p_status = 2
            sgf = sgf.parse()
            valid_events = sgf.check_validity()[0]
            if sgf.league_valid:
                sgf.save()
                sgf.update_related(valid_events)
                message = " Succesfully created a SGF"
                messages.success(request, message)
            else:
                message = " the sgf didn't seems to pass the tests"
                messages.success(request, message)
    return HttpResponseRedirect(reverse('league:admin'))


@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def upload_sgf(request):  # pylint: disable=inconsistent-return-statements
    """THis view allow user to preview sgf with wgo along with valid status of the sgf.
        Can call save_sgf from it.
    """
    if request.method == 'POST':
        form = SgfAdminForm(request.POST)
        if form.is_valid():
            sgf = Sgf()
            sgf.sgf_text = form.cleaned_data['sgf']
            sgf.p_status = 2
            sgf = sgf.parse()
            valid_events, errors = sgf.check_validity()
            form = SgfAdminForm(initial={'sgf': sgf.sgf_text})

            context = {
                'sgf': sgf,
                'form': form,
                'valid_events': valid_events,
                'errors': errors
            }
            template = loader.get_template('league/admin/upload_sgf.html')
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
            valid_events, errors = sgf.check_validity()
            form = SgfAdminForm(initial={'sgf': sgf.sgf_text})
            context = {
                'sgf': sgf,
                'form': form,
                'valid_events': valid_events,
                'errors': errors
            }
            template = loader.get_template('league/admin/upload_sgf.html')
            return HttpResponse(template.render(context, request))
        else:
            raise Http404("What are you doing here ?")


@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def admin_save_sgf(request, sgf_id):
    """update an existing sgf"""
    sgf = get_object_or_404(Sgf, pk=sgf_id)
    if request.method == 'POST':
        form = SgfAdminForm(request.POST)
        if form.is_valid():
            sgf.sgf_text = form.cleaned_data['sgf']
            sgf.urlto = form.cleaned_data['url']
            sgf.p_status = 2
            sgf = sgf.parse()
            valid_events = sgf.check_validity()[0]
            sgf.update_related(valid_events)
            sgf.save()
    message = 'successfully saved the sgf in the db'
    messages.success(request, message)
    return HttpResponseRedirect(reverse('league:edit_sgf', args=[sgf.pk]))


@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def admin_delete_sgf(request, sgf_id):
    """Delete a sgf from database."""
    sgf = get_object_or_404(Sgf, pk=sgf_id)
    if request.method == 'POST':
        message = 'successfully deleted the sgf ' + str(sgf)
        messages.success(request, message)
        sgf.delete()
        return HttpResponseRedirect(reverse('league:admin'))
    else:
        raise Http404("What are you doing here ?")


@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def admin_edit_sgf(request, sgf_id):  # pylint: disable=inconsistent-return-statements
    """Show sgf preview in wgo and test if sgf is valid.
        Allow user to change raw sgf data in text field.
        Admin can call delete_sgf or save_sgf after preview.
    """
    sgf = get_object_or_404(Sgf, pk=sgf_id)
    if request.method == 'POST':
        form = SgfAdminForm(request.POST)
        if form.is_valid():
            sgf.sgf_text = form.cleaned_data['sgf']
            sgf.urlto = form.cleaned_data['url']
            sgf.p_status = 2
            sgf = sgf.parse()
            valid_events, errors = sgf.check_validity()
            form = SgfAdminForm(initial={'sgf': sgf.sgf_text, 'url': sgf.urlto})
            context = {
                'sgf': sgf,
                'form': form,
                'preview': True,
                'valid_events': valid_events,
                'errors': errors
            }
            template = loader.get_template('league/admin/sgf_edit.html')
            return HttpResponse(template.render(context, request))
    else:
        form = SgfAdminForm(initial={'sgf': sgf.sgf_text, 'url': sgf.urlto})
        valid_events = sgf.events.all()
        context = {
            'form': form,
            'sgf': sgf,
            'preview': False,
            'valid_events': valid_events
        }
        return render(request, 'league/admin/sgf_edit.html', context)


class LeagueEventUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """ Update a league"""

    form_class = LeagueEventForm
    model = LeagueEvent
    template_name_suffix = '_update_form'

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_league_admin(self.get_object())

    def get_login_url(self):
        return '/'

    def get_success_url(self):
        return reverse('league:admin_events')

    def get_context_data(self, **kwargs):
        context = super(LeagueEventUpdate, self).get_context_data(**kwargs)
        league = self.get_object()
        context['other_events'] = league.get_other_events
        return context

class DivisionUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """ Update a division"""
    model = Division
    fields = ['informations']
    template_name_suffix = '_update_form'

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (
            user.leagueplayer_set.filter(division=self.get_object()).exists()
            or user.is_league_admin(self.get_object().league_event)
            )

    def get_login_url(self):
        return '/accounts/login/'

    def get_success_url(self):
        return reverse('league:results', kwargs={
            'event_id': self.get_object().league_event.pk,
            'division_id': self.get_object().pk
        })



class LeagueEventCreate(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create a league"""
    form_class = LeagueEventForm
    model = LeagueEvent
    template_name_suffix = '_create_form'

    def test_func(self):
        return self.request.user.is_league_admin()

    def get_login_url(self):
        return '/'

    def get_success_url(self):
        return reverse('league:admin_events')

    def get_initial(self):
        copy_from_pk = self.kwargs.get('copy_from_pk', None)
        initials = {
            'begin_time': datetime.datetime.now(),
            'end_time': datetime.datetime.now()
        }
        if copy_from_pk is not None:
            copy_from = get_object_or_404(LeagueEvent, pk=copy_from_pk)
            initials.update({
                'event_type': copy_from.event_type,
                'nb_matchs': copy_from.nb_matchs,
                'ppwin': copy_from.ppwin,
                'pploss': copy_from.pploss,
                'description': copy_from.description,
                'prizes': copy_from.prizes,
                'community': copy_from.community,
                'min_matchs': copy_from.min_matchs,
                'tag': copy_from.tag,
                'board_size': copy_from.board_size,
                'komi': copy_from.komi,
                'clock_type': copy_from.clock_type,
                'main_time': copy_from.main_time,
                'additional_time': copy_from.additional_time,
                'min_handicap': copy_from.min_handicap,
                'max_handicap': copy_from.max_handicap,
                'additional_informations': copy_from.additional_informations,
            })

        return initials

    def form_valid(self, form):
        response = super(LeagueEventCreate, self).form_valid(form)
        copy_from_pk = self.kwargs.get('copy_from_pk', None)
        if copy_from_pk is not None:
            copy_from = get_object_or_404(LeagueEvent, pk=copy_from_pk)
            divisions = copy_from.get_divisions()
            if len(divisions) == 1:
                division = Division.objects.create(
                    league_event=self.object,
                    name=self.object.name
                )
            else:
                for division in divisions:
                    division.league_event = self.object
                    division.pk = None
                    division.save()
        return response

    def get_context_data(self, **kwargs):
        context = super(LeagueEventCreate, self).get_context_data(**kwargs)
        copy_from_pk = self.kwargs.get('copy_from_pk', None)
        if copy_from_pk is not None:
            copy_from = get_object_or_404(LeagueEvent, pk=copy_from_pk)
            context['copy_from'] = copy_from
        return context


@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def admin_events(request, event_id=None):
    """List all leagues for admins"""
    events = LeagueEvent.objects.all().order_by("-begin_time")
    primary_event = Registry.get_primary_event().pk
    edit_event = -1
    if event_id is not None:
        edit_event = get_object_or_404(LeagueEvent, pk=event_id)

    template = loader.get_template('league/admin/events.html')
    context = {'events': events,
               'edit_event': edit_event,
               'primary_pk': primary_event}
    return HttpResponse(template.render(context, request))


@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def admin_events_set_primary(request, event_id):
    """Set an event primary event."""
    event = get_object_or_404(LeagueEvent, pk=event_id)
    if request.method == 'POST':
        form = ActionForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['action'] == "set_primary":
                r = Registry.objects.get(pk=1)
                r.primary_event = event
                r.save()
                message = "Changed primary event to \"{}\"".format(r.primary_event.name)
                messages.success(request, message)
                return HttpResponseRedirect(reverse('league:admin_events'))
    raise Http404("What are you doing here ?")


@login_required()
def admin_delete_division(request, division_id):
    """Delete a division"""
    division = get_object_or_404(Division, pk=division_id)
    event = division.league_event
    if not request.user.is_league_admin(event):
        raise Http404("What are you doing here ?")
    if request.method == 'POST':
        form = ActionForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['action'] == "delete_division":
                nb_players = division.number_players()
                if nb_players > 0:
                    message = "You just deleted the division" + str(division) + " and the " + str(
                        nb_players) + " players in it."
                else:
                    message = "You just deleted the empty division" + str(division) + "."
                division.delete()
                messages.success(request, message)
                return HttpResponseRedirect(form.cleaned_data['next'])
    raise Http404("What are you doing here ?")


@login_required()
def admin_events_delete(request, event_id):
    """Delete a league."""
    event = get_object_or_404(LeagueEvent, pk=event_id)
    if not request.user.is_league_admin(event):
        raise Http404("What are you doing here ?")
    if not request.method == 'POST':
        raise Http404("What are you doing here ?")

    form = ActionForm(request.POST)
    if not form.is_valid():
        raise Http404("What are you doing here ? (Token Error)")

    message = 'Successfully deleted the event ' + str(event)
    messages.success(request, message)
    event.delete()
    if 'next' in form.cleaned_data:
        return HttpResponseRedirect(form.cleaned_data['next'])
    else:
        return HttpResponseRedirect(reverse('league:admin_events'))


@login_required()
def admin_create_division(request, event_id):
    """Create a division."""
    event = get_object_or_404(LeagueEvent, pk=event_id)
    if not request.user.is_league_admin(event):
        raise Http404("What are you doing here ?")

    if request.method == 'POST':
        form = DivisionForm(request.POST)
        if form.is_valid():
            division = form.save(commit=False)
            division.league_event = event
            division.order = event.last_division_order() + 1
            division.save()
        if 'next' in form.cleaned_data:
            return HttpResponseRedirect(form.cleaned_data['next'])
        else:
            return HttpResponseRedirect(reverse('league:admin_events_update', kwargs={'pk': event_id}))
    else:
        raise Http404("What are you doing here ?")


@login_required()
def admin_rename_division(request, division_id):
    """Rename a division"""
    division = get_object_or_404(Division, pk=division_id)
    event = division.league_event
    if not request.user.is_league_admin(event):
        raise Http404("What are you doing here ?")

    if request.method == 'POST':
        form = DivisionForm(request.POST)
        if form.is_valid():
            message = "You renamed " + str(division) + " to " + form.cleaned_data['name']
            division.name = form.cleaned_data['name']
            division.save()
            messages.success(request, message)
            return HttpResponseRedirect(form.cleaned_data['next'])
    raise Http404("What are you doing here ?")


@login_required()
def admin_division_up_down(request, division_id):
    """Changing division order.
    Note that if admin have deleted a division, the order change might not be just +-1
    """
    division_1 = get_object_or_404(Division, pk=division_id)
    event = division_1.league_event
    if not request.user.is_league_admin(event):
        raise Http404("What are you doing here ?")
    if request.method == 'POST':
        form = ActionForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['action'] == "division_up" and not division_1.is_first():
                order = division_1.order
                while not event.division_set.exclude(pk=division_1.pk).filter(order=order).exists():
                    order -= 1
                division_2 = Division.objects.get(league_event=division_1.league_event, order=order)
                order_2 = division_1.order
                division_2.order = -1
                division_2.save()
                division_1.order = order
                division_1.save()
                division_2.order = order_2
                division_2.save()
            if form.cleaned_data['action'] == "division_down" and not division_1.is_last():
                order = division_1.order
                while not event.division_set.exclude(pk=division_1.pk).filter(order=order).exists():
                    order += 1
                division_2 = Division.objects.get(league_event=division_1.league_event, order=order)
                order_2 = division_1.order
                division_2.order = -1
                division_2.save()
                division_1.order = order
                division_1.save()
                division_2.order = order_2
                division_2.save()
            if 'next' in form.cleaned_data:
                return HttpResponseRedirect(form.cleaned_data['next'])
            else:
                return HttpResponseRedirect(reverse('league:admin_events_update', kwargs={'pk': event.pk}))
    raise Http404("What are you doing here ?")

@login_required
@user_passes_test(User.is_osr_admin, login_url="/", redirect_field_name=None)
def division_set_winner(request, division_id):
    '''set the winner for a division'''
    division = get_object_or_404(Division, pk=division_id)
    if request.method == 'POST':
        form = ActionForm(request.POST)
        if form.is_valid():
            user_id = form.cleaned_data['user_id']
            if user_id < 0:
                division.winner = None
            else:
                user = get_object_or_404(User, pk=user_id)
                division.winner = user
            division.save()
            return HttpResponseRedirect(form.cleaned_data['next'])
    raise Http404("What are you doing here ?")

@login_required()
def division_create_wont_play(request, division_id):
    division = get_object_or_404(Division, pk=division_id)
    event = division.league_event
    if not request.user.is_league_admin(event):
        raise Http404("What are you doing here ?")
    form = AddWontPlayForm(request.POST)
    if form.is_valid():
        try:
            users = [User.objects.get(pk=pk) for pk in form.cleaned_data['players']]
            if all([division.has_user(user) for user in users]):
                Sgf.create_wont_play(event, division, users)
        except:
            pass
    return division_update_wont_play(request, division.pk)

@login_required()
def division_remove_wont_play(request, division_id):
    division = get_object_or_404(Division, pk=division_id)
    event = division.league_event
    if not request.user.is_league_admin(event):
        raise Http404("What are you doing here ?")
    form = RemoveWontPlayForm(request.POST)
    if form.is_valid():
        for pk in form.cleaned_data['sgfs']:
            Sgf.objects.filter(pk=pk).delete()
    return division_update_wont_play(request, division.pk)

@login_required()
def division_update_wont_play(request, division_id):
    division = get_object_or_404(Division, pk=division_id)
    event = division.league_event
    if not request.user.is_league_admin(event):
        raise Http404("What are you doing here ?")
    context = {
        'event_pk': event.pk,
        'division': division,
    }
    print(event.pk)
    return render(request, 'league/admin/update_wont_play.html', context)

@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def populate(request, to_event_id, from_event_id=None):
    """
    A view that helps admin to do populate at the end of the month.
    It displays users from primary_event and let the admin choose to which division they will be in next event.
    This view can perform a preview loading data from the form. Actual db populating happen in proceed_populate view

    """
    to_event = get_object_or_404(LeagueEvent, pk=to_event_id)
    if not request.user.is_league_admin(to_event):
        raise Http404("What are you doing here ?")
    new_players = OrderedDict()

    for division in to_event.get_divisions():
        new_players[division.name] = []

    if request.method == 'POST':
        if from_event_id is None:
            raise Http404("What are you doing here ?")
        from_event = get_object_or_404(LeagueEvent, pk=from_event_id)

        form = LeaguePopulateForm(from_event, to_event, request.POST)
        if form.is_valid():
            divisions = from_event.get_divisions()
            for division in divisions:
                division.results = division.get_results()
                for player in division.results:
                    if player.is_active and form.cleaned_data['player_' + str(player.pk)] != '0':
                        new_division = Division.objects.get(pk=form.cleaned_data['player_' + str(player.pk)])
                        new_player = LeaguePlayer(
                            user=player.user,
                            event=to_event,
                            kgs_username=player.kgs_username,
                            division=new_division
                        )
                        new_player.previous_division = player.division
                        new_players[new_division.name].append(new_player)
            # Admin have a preview so we are sure form is not dumber than the admin.
            # We will display the save button in template
            preview = True
    else:
        if 'from_event' in request.GET:
            from_event = get_object_or_404(LeagueEvent, pk=request.GET['from_event'])
        else:
            raise Http404("What are you doing here ?")
        form = LeaguePopulateForm(from_event, to_event)
        # Having preview at false prevent the save button to be displayed in tempalte
        preview = False

        divisions = from_event.get_divisions()
        for division in divisions:
            division.results = division.get_results()

    context = {
        'from_event': from_event,
        'to_event': to_event,
        'form': form,
        'new_players': new_players,
        'preview': preview,
        'divisions': divisions
    }
    template = loader.get_template('league/admin/populate.html')
    return HttpResponse(template.render(context, request))




@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def proceed_populate(request, from_event_id, to_event_id):
    """ Here we actually populate the db with the form from populate view.
    We assume the admin have seen the new events structure in a preview before being here.
    """

    # populate view should have the admin select this event and sending this here in the form.

    to_event = get_object_or_404(LeagueEvent, pk=to_event_id)
    if not request.user.is_league_admin(to_event):
        raise Http404("What are you doing here ?")
    from_event = get_object_or_404(LeagueEvent, pk=from_event_id)
    if request.method == 'POST':
        form = LeaguePopulateForm(from_event, to_event, request.POST)
        if form.is_valid():
            n = 0
            for player in from_event.get_players():
                if player.nb_games() >= from_event.min_matchs and form.cleaned_data['player_' + str(player.pk)] != '0':
                    n += 1
                    new_division = Division.objects.get(pk=form.cleaned_data['player_' + str(player.pk)])
                    LeaguePlayer.objects.create(user=player.user,
                                                event=to_event,
                                                kgs_username=player.kgs_username,
                                                ogs_username=player.ogs_username,
                                                division=new_division)
        message = "The new " + to_event.name + " was populated with " + str(n) + " players."
        messages.success(request, message)
        if request.user.is_league_admin():
            return HttpResponseRedirect(reverse('league:admin_events'))
        else:
            return HttpResponseRedirect(reverse(
                'community:community_page',
                args=[to_event.community.slug]
            ))
    else:
        raise Http404("What are you doing here ?")


@login_required()
@user_passes_test(User.is_osr_admin, login_url="/", redirect_field_name=None)
def admin_user_send_mail(request, user_id):  # pylint: disable=inconsistent-return-statements
    """Send an email to a user."""
    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            if len(form.cleaned_data['copy_to']) > 0:
                recipients = [
                    user.get_primary_email().email,
                    form.cleaned_data['copy_to']
                ]
            else:
                recipients = [user.get_primary_email().email]
            send_mail(
                form.cleaned_data['subject'],
                form.cleaned_data['message'],
                'openstudyroom@gmail.com',
                recipients,
                fail_silently=False,
            )
            pm_write(
                request.user,
                user,
                form.cleaned_data['subject'],
                body=form.cleaned_data['message'],
                skip_notification=True,
            )
            message = "Successfully sent an email and a message to " + str(user)
            messages.success(request, message)
            return HttpResponseRedirect(reverse('league:admin'))
    else:
        form = EmailForm()
        context = {'form': form, 'user': user}
        return render(request, 'league/admin/user_send_mail.html', context)


def discord_redirect(request):
    """loads discord invite url from discord_url_file and redirects the user if he passes the tests.
        deprecated. Should be removed since OSR discord is public now.
    """
    if request.user.is_authenticated and request.user.is_league_member:
        with open(discord_url_file) as f:
            disc_url = f.read().strip()
        return HttpResponseRedirect(disc_url.replace('\n', ''))
    else:
        message = "OSR discord server is for members only."
        messages.success(request, message)
        return HttpResponseRedirect('/')


@login_required()
@user_passes_test(User.is_osr_admin, login_url="/", redirect_field_name=None)
def update_all_sgf_check_code(request):
    """
    Reparse all sgf from db. This can be usefull after adding a new field to sgf models.
    We just display a confirmation page with a warning if no post request.
    For now, we will just update the check_code field.
    Latter, we might add a select form to select what field(s) we want update
    """
    if request.method == 'POST':
        form = ActionForm(request.POST)
        if form.is_valid():
            sgfs = Sgf.objects.all()
            for sgf in sgfs:
                sgf_prop = utils.parse_sgf_string(sgf.sgf_text)
                sgf.check_code = sgf_prop['check_code']
                sgf.save()
            message = "Successfully updated " + str(sgfs.count()) + " sgfs."
            messages.success(request, message)
            return HttpResponseRedirect(reverse('league:admin'))
        else:
            message = "Something went wrong (form is not valid)"
            messages.success(request, message)
            return HttpResponseRedirect(reverse('league:admin'))
    else:

        return render(request, 'league/admin/update_all_sgf_check_code.html')


@login_required()
@user_passes_test(User.is_osr_admin, login_url="/", redirect_field_name=None)
def admin_users_list(request, event_id=None, division_id=None):
    """Show all users for admins."""
    event = None
    division = None
    if event_id is None:
        users = User.objects.all()
    else:
        event = get_object_or_404(LeagueEvent, pk=event_id)
        if division_id is None:
            players = event.leagueplayer_set.all()
            users = User.objects.filter(leagueplayer__in=players)
        else:
            division = get_object_or_404(Division, pk=division_id)
            players = division.leagueplayer_set.all()
            users = User.objects.filter(leagueplayer__in=players)
    context = {
        'users': users,
        'event': event,
        'division': division,
    }
    return render(request, 'league/admin/users.html', context)



@login_required()
@user_passes_test(User.is_osr_admin, login_url="/", redirect_field_name=None)
def create_profile(request, user_id):
    """Create profiles for a user."""
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        form = ActionForm(request.POST)
        if form.is_valid():
            profile = Profile(user=user)
            profile.save()
            message = "Successfully created a profile for " + user.username + " ."
            messages.success(request, message)
            return HttpResponseRedirect(reverse('league:admin'))
        else:
            message = "Something went wrong (form is not valid)"
            messages.success(request, message)
            return HttpResponseRedirect(reverse('league:admin'))
    else:
        return render(request, 'league/admin/create_all_profiles.html')


class ProfileUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update a user profile"""
    form_class = ProfileForm
    model = Profile
    template_name_suffix = '_update'

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and \
            user.is_league_member() and \
            self.get_object().user == user

    def get_login_url(self):
        return '/'

    def get_success_url(self):
        return '/league/account/'

    def form_valid(self, form):
        # pylint: disable=attribute-defined-outside-init
        self.object = form.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_object(self, queryset=None):
        if 'pk' in self.kwargs:
            return super().get_object(queryset)
        else:
            return self.model.objects.get(pk=self.request.user.profile.pk)


@login_required()
@user_passes_test(User.is_osr_admin, login_url="/", redirect_field_name=None)
def update_all_profiles(request):
    """Update all profiles. We use this view to fix datas from time to time"""
    if request.method == 'POST':
        form = ActionForm(request.POST)
        if form.is_valid():
            # replace all FFG "0" by empty string
            profiles = Profile.objects.filter(ffg_licence_number="0")
            profiles.update(ffg_licence_number="")
            message = "Successfully updated " + str(profiles.count()) + " profiles."
            messages.success(request, message)
            return HttpResponseRedirect(reverse('league:admin'))
        else:
            message = "Something went wrong (form is not valid)"
            messages.success(request, message)
            return HttpResponseRedirect(reverse('league:admin'))
    else:
        return render(request, 'league/admin/update_all_profiles.html')

@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def download_ffg_tou(request, league_id):
    """
    On GET we serve a html that allow admin to add missing FFG licence number.
    On POST we render and download the tou file for https://ffg.jeudego.org/echelle/format_res.php
    """
    league = get_object_or_404(LeagueEvent, pk=league_id)
    if not request.user.is_league_admin(league):
        return Http404()

    if request.method == 'POST':
        # Is it proper? we are reading all POST datas except csrfmiddlewaretoken as licence number.
        licences = {i:request.POST[i] for i in request.POST if i != 'csrfmiddlewaretoken'}
        tou = format_ffg_tou(league, licences)

        if tou is None:
            message = "Something went wrong. Probably a player with a wrong FFG licence number"
            messages.success(request, message)
            return HttpResponseRedirect('/')

        filename = f'OSR-league-{timezone.now().strftime("%m/%Y")}.tou'
        response = HttpResponse(tou, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename={0}'.format(filename)
        return response

    context = {}
    league = get_object_or_404(LeagueEvent, pk=league_id)
    players = league.leagueplayer_set.all().prefetch_related('user__profile')
    context['league'] = league
    context['users'] = [players.user for players in players]
    return render(request, 'league/admin/download_ffg_tou.html', context)
