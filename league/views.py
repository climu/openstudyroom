from collections import OrderedDict
import json
import datetime
from time import sleep

from django.shortcuts import get_object_or_404, render
from django.template import loader
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
from django.db.models import Q, Prefetch
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.mail import send_mail
from django.views.generic.edit import CreateView, UpdateView
from django.template.defaultfilters import date as _date, time as _time
from django.utils import timezone
from machina.core.db.models import get_model
from postman.api import pm_write
import pytz
import requests

from . import utils
from .models import Sgf, LeaguePlayer, User, LeagueEvent, Division, Registry, \
    Profile
from .forms import SgfAdminForm, ActionForm, LeaguePopulateForm, UploadFileForm, DivisionForm, LeagueEventForm, \
    EmailForm, TimezoneForm, ProfileForm

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
    r = utils.kgs_connect()
    for m in json.loads(r.text)['messages']:
        if m['type'] == 'ROOM_JOIN' and m['channelId'] == 3627409:
            for kgs_user in m['users']:
                profile = Profile.objects.filter(kgs_username__iexact=kgs_user['name']).first()
                if profile is not None:
                    profile.last_kgs_online = now
                    profile.save()
    # 3 wait a bit
    sleep(2)

    # 4.1 look for some sgfs that we analyse and maybe record as games
    sgf = Sgf.objects.filter(p_status=2).first()
    if sgf is None:
        sgf = Sgf.objects.filter(p_status=1).first()
    if sgf is not None:
        # parse the sgf datas to populate the rows -> KGS archive request
        sgf = sgf.parse()
        # if the sgf doesn't have a result (unfinished game) we just delete it
        # If the game was a OGS private game result will also be '?'. See models.sgf.parse
        if sgf.result == '?':
            sgf.delete()
        else:
            valid_events = sgf.check_validity()
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
    response['Content-Disposition'] = 'attachment; filename="' +  \
        sgf.wplayer + '-' + sgf.bplayer + '-' + sgf.date.strftime('%m/%d/%Y') + '.sgf"'
    return response


def list_games(request, event_id=None, sgf_id=None):
    """List all games and allow to show one with wgo."""
    open_events = LeagueEvent.get_events(request.user).filter(is_open=True)

    context = {'open_events': open_events}
    if sgf_id is not None:
        sgf = get_object_or_404(Sgf, pk=sgf_id, league_valid=True)
        context.update({'sgf': sgf})

    if event_id is None:
        sgfs = Sgf.objects.defer('sgf_text').filter(league_valid=True).\
            prefetch_related('white', 'black', 'winner').\
            select_related('white__profile', 'black__profile').\
            order_by('-date')
        context.update({'sgfs': sgfs})
        template = loader.get_template('league/archives_games.html')

    else:
        event = get_object_or_404(LeagueEvent, pk=event_id)
        sgfs = event.sgf_set.only(
            'date',
            'black',
            'white',
            'winner',
            'result',
            'league_valid').filter(league_valid=True).\
            prefetch_related('white', 'black', 'winner').\
            select_related('white__profile', 'black__profile').\
            order_by('-date')
        template = loader.get_template('league/games.html')
        can_join = event.can_join(request.user)
        context.update({
            'sgfs': sgfs,
            'event': event,
            'can_join': can_join,
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
    if division is None:
        results = None
    else:
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
        'can_join': can_join,
        'number_players': number_players
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

def archives(request):
    """Show a list of all leagues."""
    events = LeagueEvent.get_events(request.user)
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
    context = {
        'event': event,
        'open_events': open_events,
        'can_join': can_join,
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
                    queryset=Sgf.objects.defer('sgf_text').all()
                ),
                Prefetch(
                    'white_sgf',
                    queryset=Sgf.objects.defer('sgf_text').all()
                ),
                'profile')
        users = [user.get_stats for user in users]
        context = {
            'users': users,
            'open_events': open_events,
        }
        template = loader.get_template('league/archives_players.html')
    else:
        event = get_object_or_404(LeagueEvent, pk=event_id)
        can_join = event.can_join(request.user)
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
        }
        template = loader.get_template('league/players.html')
    return HttpResponse(template.render(context, request))


@login_required()
@user_passes_test(User.is_league_member, login_url="/", redirect_field_name=None)
def join_event(request, event_id, user_id):
    """Add a user to a league. After some check we calls the models.LeagueEvent.join_event method."""
    event = get_object_or_404(LeagueEvent, pk=event_id)
    # No one should join a close event
    if not event.is_open:
        message = "You can't join a close event !"
        messages.success(request, message)
        return HttpResponseRedirect(reverse('league:league_account'))
    user = get_object_or_404(User, pk=user_id)
    # We already know that request.user is a league member.
    # So he can join an open event by himself.
    # If he is a league admin, he can make another user
    if request.user.is_league_admin or request.user == user:
        if request.method == 'POST':
            form = ActionForm(request.POST)
            if form.is_valid() and form.cleaned_data['action'] == 'join':
                division = event.last_division()
                if not division:  # the event have no division
                    message = "The Event you tryed to join have no division. That's strange."
                else:
                    if user.join_event(event, division):
                        meijin_league = LeagueEvent.objects.filter(
                            event_type='meijin',
                            is_open=True,
                            community__isnull=True
                        ).order_by('end_time').first()
                        meijin_division = meijin_league.division_set.first()
                        user.join_event(meijin_league, meijin_division)
                        message = "Welcome in " + division.name + " ! You can start playing right now."
                    else:
                        message = "Oops ! Something went wrong. You didn't join."
                messages.success(request, message)
                return HttpResponseRedirect(form.cleaned_data['next'])
    else:
        message = "What are you doing here?"
        messages.success(request, message)
    return HttpResponseRedirect('/')


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
        #user = User.objects.get(username=user_name)

    if not user.is_league_member():
        return HttpResponseRedirect('/')

    open_events = LeagueEvent.get_events(request.user).filter(is_open=True)

    players = user.leagueplayer_set.order_by('-pk')

    sgfs = Sgf.objects.defer('sgf_text').filter(Q(white=user) | Q(black=user)).\
        prefetch_related('white', 'black', 'winner').\
        select_related('white__profile', 'black__profile')
    if len(sgfs) == 0:
        sgfs = None
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
    context = {
        'players': players,
        'open_events': open_events,
        'sgfs': sgfs,
        'user': user,
    }
    template = loader.get_template('league/account.html')
    return HttpResponse(template.render(context, request))


def game_api(request, sgf_id):
    """Returns a json to be use in game pages. Json is formated as:
    'infos': players, date, league, group, permalink, download link.
    'sgf': sgf datas as plain text string
    """
    sgf = get_object_or_404(Sgf, pk=sgf_id)
    html = loader.render_to_string("league/includes/game_info.html", {'sgf': sgf})
    data = {}
    data['sgf'] = sgf.sgf_text.replace(';B[]', "").replace(';W[]', "")
    data['permalink'] = '/league/games/' + str(sgf.pk) + '/'
    data['game_infos'] = html
    data['white'] = sgf.white.kgs_username
    data['black'] = sgf.black.kgs_username

    return HttpResponse(json.dumps(data), content_type="application/json")


def scrap_list(request):
    open_events = LeagueEvent.objects.filter(is_open=True)
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


#################################################################
####    ADMINS views    #########################################
#################################################################


@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
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
        if user.groups.filter(name='new_user').exists():
            if action == "welcome":
                user.groups.clear()
                group = Group.objects.get(name='league_member')
                user.groups.add(group)
                utils.quick_send_mail(user, 'emails/welcome.txt')
            
                if settings.DEBUG:
                    discord_url = 'http://example.com/' # change this for local test
                else:
                    with open('/etc/discord_hook_url.txt') as f:
                discord_url = f.read().strip()                

                welcome = "Please welcome our new member " + user.username + " with a violent game of baduk. \n"

                if not user.profile.kgs_username:
                    kname = ""
                else: 
                    kname = "KGS : " + user.profile.kgs_username + " \n"

                if not user.profile.ogs_username:
                    oname = ""
                else: 
                    oname = "OGS : " + user.profile.ogs_username + " " + "[https://online-go.com/player/" + str(user.profile.ogs_id) + "/]"
                                
                values = {"content":  welcome + kname + oname} 

                r = requests.post(discord_url, json=values)

            elif action[0:6] == "delete":
                if action[7:15] == "no_games":# deletion due to no played games
                    utils.quick_send_mail(user, 'emails/no_games.txt')
                user.delete()
        else:
            return HttpResponse('failure')
        return HttpResponse('succes')

    # on normal /league/admin load
    else:
        new_users = User.objects.filter(groups__name='new_user')
        # get url of admin board if debug = False
        if settings.DEBUG:
            board_url = 'https://mensuel.framapad.org/p/1N0qTQCsk6?showControls=true&showChat=false&showLineNumbers=false&useMonospaceFont=false'
        else:
            with open('/etc/admin_board_url.txt') as f:
                board_url = f.read().strip()
        context = {
            'new_users': new_users,
            'board_url': board_url,
        }
        template = loader.get_template('league/admin/dashboard.html')
        return HttpResponse(template.render(context, request))


@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def admin_set_meijin(request):
    """Set one user to be meijin. Calls user.set_meijin methods."""
    if request.method == 'POST':
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


# Next 3 views handle sgf upload.
# Worklfow is: handle_upload_sgf -> upload_sgf -> create_sgf


@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def handle_upload_sgf(request):
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
            return HttpResponseRedirect(reverse('league:upload_sgf'))
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
            valid_events = sgf.check_validity()
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
def upload_sgf(request):
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
            valid_events = sgf.check_validity()
            form = SgfAdminForm(initial={'sgf': sgf.sgf_text})

            context = {
                'sgf': sgf,
                'form': form,
                'valid_events': valid_events,
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
            valid_events = sgf.check_validity()
            form = SgfAdminForm(initial={'sgf': sgf.sgf_text})
            context = {
                'sgf': sgf,
                'form': form,
                'valid_events': valid_events,
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
            valid_events = sgf.check_validity()
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
def admin_edit_sgf(request, sgf_id):
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
            valid_events = sgf.check_validity()
            form = SgfAdminForm(initial={'sgf': sgf.sgf_text, 'url': sgf.urlto})
            context = {
                'sgf': sgf,
                'form': form,
                'preview': True,
                'valid_events': valid_events
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
        if self.request.user.is_league_admin():
            return reverse('league:admin_events')
        else:
            return reverse(
                'community:community_page',
                kwargs={'name': self.get_object().community.name}
            )

    def get_context_data(self, **kwargs):
        context = super(LeagueEventUpdate, self).get_context_data(**kwargs)
        league = self.get_object()
        if league.community is None:
            context['other_events'] = league.get_other_events
        else:
            context['other_events'] = league.get_other_events().filter(community=league.community)
        return context

class LeagueEventCreate(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create a league"""
    form_class = LeagueEventForm
    model = LeagueEvent
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
                return HttpResponseRedirect(
                    reverse('league:admin_events_update', kwargs={'pk': event.pk}))

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
            return HttpResponseRedirect(
                reverse('league:admin_events_update', kwargs={'pk': event.pk}))
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
            return HttpResponseRedirect(
                reverse('league:admin_events_update', kwargs={'pk': event.pk}))
    raise Http404("What are you doing here ?")


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
        else:
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
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def admin_user_send_mail(request, user_id):
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
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
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
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
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
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def create_all_profiles(request):
    """Create all profiles for users. Should be removed now"""
    if request.method == 'POST':
        form = ActionForm(request.POST)
        if form.is_valid():
            users = User.objects.filter(profile__isnull=True)
            for user in users:
                profile = Profile(user=user, kgs_username=user.kgs_username)
                profile.save()
            message = "Successfully created " + str(users.count()) + " profiles."
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
        return user.is_authenticated() and \
            user.is_league_member() and \
            self.get_object().user == user

    def get_login_url(self):
        return '/'

    def get_success_url(self):
        return '/league/account/'

    def form_valid(self, form):
        # pylint: disable=attribute-defined-outside-init
        self.object = form.save()
        # do something with self.object
        return HttpResponseRedirect(self.get_success_url())


@login_required()
@user_passes_test(User.is_league_admin, login_url="/", redirect_field_name=None)
def update_all_profile_ogs(request):
    """Update all profiles OGS ids. Should be removed now"""
    if request.method == 'POST':
        form = ActionForm(request.POST)
        if form.is_valid():
            profiles = Profile.objects.filter(ogs_id__gt=0)
            for profile in profiles:
                open_players = profile.user.leagueplayer_set.filter(event__is_open=True)
                open_players.update(ogs_username=profile.ogs_username)
            message = "Successfully updated " + str(profiles.count()) + " sgfs."
            messages.success(request, message)
            return HttpResponseRedirect(reverse('league:admin'))
        else:
            message = "Something went wrong (form is not valid)"
            messages.success(request, message)
            return HttpResponseRedirect(reverse('league:admin'))
    else:
        return render(request, 'league/admin/update_all_profile_ogs.html')
