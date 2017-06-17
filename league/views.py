from django.shortcuts import get_object_or_404, render
from django.template import loader
from django.http import HttpResponse, HttpResponseRedirect, Http404
from .models import Sgf, LeaguePlayer, User, LeagueEvent, Division, Game, Registry, is_league_admin, \
    is_league_member, Profile
from .forms import SgfAdminForm, ActionForm, LeaguePopulateForm, UploadFileForm, DivisionForm, LeagueEventForm, \
    EmailForm, TimezoneForm
import datetime
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from collections import OrderedDict
from . import utils
from django.core.mail import send_mail
from django.views.generic.edit import UpdateView
from django.views.generic.edit import CreateView
from machina.core.db.models import get_model
import json

ForumProfile = get_model('forum_member', 'ForumProfile')
discord_url_file = "/etc/discord_url.txt"


def scraper():
    """Check kgs to update our db.
    This is called every 5 mins by cron in production.
    To prevent overrequestion kgs, do one of the 3 actions only:
    - 1 check time since get from kgs
    - 2 look for some sgfs that analyse and maybe pulled as games
    - 3 check a player
    """

    # 1 check time since get from kgs
    now = datetime.datetime.now().replace(tzinfo=None)
    last_kgs = Registry.get_time_kgs().replace(tzinfo=None)
    delta = now - last_kgs
    delta_sec = delta.total_seconds()
    kgs_delay = Registry.get_kgs_delay()
    if delta_sec < kgs_delay:  # we can't scrape yet
        out = 'too soon'
        return out
    # 2 look for some sgfs that we analyse and maybe record as games
    sgfs = Sgf.objects.filter(p_status=2)
    if len(sgfs) == 0:
        sgfs = Sgf.objects.filter(p_status=1)
    if len(sgfs) > 0:
        sgf = sgfs[0]
        # parse the sgf datas to populate the rows -> KGS archive request
        sgf = sgf.parse()
        # if the sgf doesn't have a result (unfinished game) we just delete it
        if sgf.result == '?':
            sgf.delete()
        else:
            valid_events = sgf.check_validity()
            sgf.update_related(valid_events)
            sgf.save()
            # I think we could deal with sgf already in db one day here:
            # Populate existing sgf urlto and delete new sgf
        out = sgf
    # 3 no games to scrap let's check a player
    else:
        events = LeagueEvent.objects.filter(is_open=True)
        profiles = Profile.objects.filter(user__leagueplayer__event__in=events) \
            .distinct().order_by('-p_status')
        # if everyone has been checked.
        if not (profiles.filter(p_status__gt=0).exists()):
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
@user_passes_test(is_league_member, login_url="/", redirect_field_name=None)
def timezone_update(request):
    """Update the timezone of request.user."""
    user = request.user
    if request.method == 'POST':
        form = TimezoneForm(request.POST)
        if form.is_valid():
            user.profile.timezone = form.cleaned_data['timezone']
            user.profile.save()
            message = 'successfully updated your timezone'
            messages.success(request, message)
    form = TimezoneForm(instance=user.profile)
    context = {'user': user, 'form': form}
    template = loader.get_template('league/timezone_update.html')
    return HttpResponse(template.render(context, request))


def sgf(request, sgf_id):
    """Download one sgf file."""
    sgf = get_object_or_404(Sgf, pk=sgf_id)
    response = HttpResponse(sgf.sgf_text, content_type='application/octet-stream')
    response['Content-Disposition'] = 'attachment; filename="' +  \
        sgf.wplayer + '-' + sgf.bplayer + '-' + sgf.date.strftime('%m/%d/%Y') + '.sgf"'
    return response


def games(request, event_id=None, sgf_id=None):
    """List all games and allow to show one with wgo."""
    open_events = LeagueEvent.objects.filter(is_open=True)
    if not (request.user.is_authenticated and request.user.user_is_league_admin()):
        open_events = open_events.filter(is_public=True)
    context = {'open_events': open_events}
    if sgf_id is not None:
        sgf = get_object_or_404(Sgf, pk=sgf_id, league_valid=True)
        context.update({'sgf': sgf})

    if event_id is None:
        sgfs = Sgf.objects.filter(league_valid=True).order_by('-date')
        context.update({'sgfs': sgfs})
        template = loader.get_template('league/archives_games.html')

    else:
        event = get_object_or_404(LeagueEvent, pk=event_id)
        sgfs = event.sgf_set.filter(league_valid=True).order_by('-date')
        template = loader.get_template('league/games.html')
        can_join = event.can_join(request.user)
        context.update({
            'sgfs': sgfs,
            'event': event,
            'can_join': can_join,
        })
    return HttpResponse(template.render(context, request))


def results(request, event_id=None, division_id=None):
    """Show the reuslts of a division."""
    open_events = LeagueEvent.objects.filter(is_open=True)
    if not (request.user.is_authenticated and request.user.user_is_league_admin()):
        open_events = open_events.filter(is_public=True)
    if event_id is None:
        event = Registry.get_primary_event()
    else:
        event = get_object_or_404(LeagueEvent, pk=event_id)
    if division_id is None:
        division = Division.objects.filter(league_event=event).first()
    else:
        division = get_object_or_404(Division, pk=division_id)
    can_join = event.can_join(request.user)
    results = division.get_results()
    template = loader.get_template('league/results.html')
    context = {
        'event': event,
        'division': division,
        'results': results,
        'open_events': open_events,
        'can_join': can_join,
    }
    return HttpResponse(template.render(context, request))


def archives(request):
    """Show a list of all leagues."""
    events = LeagueEvent.objects.all()
    open_events = events.filter(is_open=True)
    if not (request.user.is_authenticated and request.user.user_is_league_admin()):
        open_events = open_events.filter(is_public=True)
        events = events.filter(is_public=True)
    context = {
        'events': events,
        'open_events': open_events,
    }
    template = loader.get_template('league/archive.html')
    return HttpResponse(template.render(context, request))


def event(request, event_id=None, division_id=None, ):
    open_events = LeagueEvent.objects.filter(is_open=True)
    if not (request.user.is_authenticated and request.user.user_is_league_admin()):
        open_events = open_events.filter(is_public=True)
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


def players(request, event_id=None, division_id=None):
    open_events = LeagueEvent.objects.filter(is_open=True)
    can_join = False
    if not (request.user.is_authenticated and request.user.user_is_league_admin()):
        open_events = open_events.filter(is_public=True)
    # if no event is provided, we show all the league members
    if event_id is None:
        users = User.objects.filter(groups__name='league_member')
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
@user_passes_test(is_league_member, login_url="/", redirect_field_name=None)
def join_event(request, event_id, user_id):
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
    if request.user.user_is_league_admin or request.user == user:
        if request.method == 'POST':
            form = ActionForm(request.POST)
            if form.is_valid():
                if form.cleaned_data['action'] == 'join':
                    division = event.last_division()
                    if not division:  # the event have no division
                        message = "The Event you tryed to join have no division. That's strange."
                    else:
                        if user.join_event(event, division):
                            message = "Welcome in " + division.name + " ! You can start playing right now."
                        else:
                            message = "Oops ! Something went wrong. You didn't join."
                    messages.success(request, message)
                    return HttpResponseRedirect(form.cleaned_data['next'])
    else:
        message = "What are you doing here ?"
        messages.success(request, message)
    return HttpResponseRedirect('/')

def account(request, user_name=None):
    """Show a user account.
    if url ask for a user( /league/user/climu) display that user profile.
    if none, we check if user is auth and, if so,  we display his own profile.
    In the template, we will display a join button only if user is auth and request.user == user
    """
    # if no user provide  by url, we check if user is auth and if so display hi own profile
    if user_name is None:
        if request.user.is_authenticated:
            user = request.user
        else:
            # maybe a view with a list of all our users might be cool redirection here
            return HttpResponseRedirect('/')
    else:
        # user = get_object_or_404(User,username = user_name)
        user = User.objects.get(username=user_name)

    if not is_league_member(user):
        return HttpResponseRedirect('/')

    open_events = LeagueEvent.objects.filter(is_open=True)
    if not (user.is_authenticated and user.user_is_league_admin()):
        open_events = open_events.filter(is_public=True)

    players = user.leagueplayer_set.order_by('-pk')
    sgfs = Sgf.objects.filter(Q(white=user) | Q(black=user))
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
    """ will return a json containing:
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


@login_required()
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def admin_sgf_list(request):
    sgfs = Sgf.objects.all()
    context = {'sgfs': sgfs}
    return render(request, 'league/admin/sgf_list.html', context)


@login_required()
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def handle_upload_sgf(request):
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
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def create_sgf(request):
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
                message = " Succesfully created a sgf and a league game"
                messages.success(request, message)
            else:
                message = " the sgf didn't seems to pass the tests"
                messages.success(request, message)
    return HttpResponseRedirect(reverse('league:admin'))


@login_required()
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def upload_sgf(request):
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
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def admin_save_sgf(request, sgf_id):
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
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def admin_delete_sgf(request, sgf_id):
    sgf = get_object_or_404(Sgf, pk=sgf_id)
    if request.method == 'POST':
        message = 'successfully deleted the sgf ' + str(sgf)
        messages.success(request, message)
        sgf.delete()
        return HttpResponseRedirect(reverse('league:admin'))
    else:
        raise Http404("What are you doing here ?")


@login_required()
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def admin_edit_sgf(request, sgf_id):
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


@login_required()
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def admin(request):
    if request.method == 'POST':
        form = ActionForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['action'] == "welcome_new_user":
                user = User.objects.get(pk=form.cleaned_data['user_id'])
                user.groups.clear()
                group = Group.objects.get(name='league_member')
                user.groups.add(group)
                # We send a welcome mail only if we have a primary email
                email = user.get_primary_email()
                if email is not None:
                    plaintext = loader.get_template('emails/welcome.txt')
                    context = {'user': user}
                    message = plaintext.render(context)
                    send_mail(
                        'Welcome in the Open Study Room',
                        message,
                        'openstudyroom@gmail.com',
                        [email.email],
                        fail_silently=False,
                    )
                message = " You moved " + user.username + "from new user to league member"
                messages.success(request, message)
                return HttpResponseRedirect(reverse('league:admin'))
            if form.cleaned_data['action'] == "delete_new_user":
                user = User.objects.get(pk=form.cleaned_data['user_id'])
                user.delete()
                message = " You just deleted " + user.username + "! Bye bye " + user.username + "."
                messages.success(request, message)
                return HttpResponseRedirect(reverse('league:admin'))
    else:
        sgfs = Sgf.objects.filter(league_valid=False, p_status=0)
        new_users = User.objects.filter(groups__name='new_user')
        form = UploadFileForm()
        context = {
            'sgfs': sgfs,
            'new_users': new_users,
            'form': form,
        }
        template = loader.get_template('league/admin/dashboard.html')
        return HttpResponse(template.render(context, request))


class LeagueEventUpdate(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    form_class = LeagueEventForm
    model = LeagueEvent
    template_name_suffix = '_update_form'

    def test_func(self):
        return self.request.user.is_authenticated() and self.request.user.user_is_league_admin()

    def get_login_url(self):
        return '/'


class LeagueEventCreate(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = LeagueEventForm
    model = LeagueEvent
    template_name_suffix = '_create_form'
    initial = {'begin_time': datetime.datetime.now(),
               'end_time': datetime.datetime.now()}

    def test_func(self):
        return self.request.user.is_authenticated() and \
            self.request.user.user_is_league_admin()

    def get_login_url(self):
        return '/'


@login_required()
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def admin_events(request, event_id=None):
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
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def admin_events_set_primary(request, event_id):
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
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def admin_delete_division(request, division_id):
    division = get_object_or_404(Division, pk=division_id)
    event = division.league_event
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
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def admin_events_delete(request, event_id):
    event = get_object_or_404(LeagueEvent, pk=event_id)
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
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def admin_create_division(request, event_id):
    event = get_object_or_404(LeagueEvent, pk=event_id)
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
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def admin_rename_division(request, division_id):
    division = get_object_or_404(Division, pk=division_id)
    event = division.league_event

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
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def admin_division_up_down(request, division_id):
    """Changing division order.
    Note that if admin have deleted a division, the order change might not be just +-1
    """
    division_1 = get_object_or_404(Division, pk=division_id)
    event = division_1.league_event
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
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def populate(request, to_event_id, from_event_id=None):
    """
    A view that helps admin to do populate at the end of the month.
    It displays users from primary_event and let the admin choose to which division they will be in next event.
    This view can perform a preview loading data from the form. Actual db populating happen in proceed_populate view

    """
    to_event = get_object_or_404(LeagueEvent, pk=to_event_id)
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
            for player in from_event.get_players():
                if player.is_active():
                    new_division = Division.objects.get(pk=form.cleaned_data['player_' + str(player.pk)])
                    new_player = LeaguePlayer(user=player.user,
                                              event=to_event,
                                              kgs_username=player.kgs_username,
                                              division=new_division)
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

    context = {
        'from_event': from_event,
        'to_event': to_event,
        'form': form,
        'new_players': new_players,
        'preview': preview,
    }
    template = loader.get_template('league/admin/populate.html')
    return HttpResponse(template.render(context, request))


@login_required()
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def proceed_populate(request, from_event_id, to_event_id):
    """ Here we actually populate the db with the form from populate view.
    We assume the admin have seen the new events structure in a preview before being here.
    """

    # populate view should have the admin select this event and sending this here in the form.

    to_event = get_object_or_404(LeagueEvent, pk=to_event_id)
    from_event = get_object_or_404(LeagueEvent, pk=from_event_id)
    if request.method == 'POST':
        form = LeaguePopulateForm(from_event, to_event, request.POST)
        if form.is_valid():
            n = 0
            for player in from_event.get_players():
                if player.is_active():
                    n += 1
                    new_division = Division.objects.get(pk=form.cleaned_data['player_' + str(player.pk)])
                    new_player = LeaguePlayer.objects.create(user=player.user,
                                                             event=to_event,
                                                             kgs_username=player.kgs_username,
                                                             division=new_division)
        message = "The new " + to_event.name + " was populated with " + str(n) + " players."
        messages.success(request, message)
        return HttpResponseRedirect(reverse('league:admin_events'))
    else:
        raise Http404("What are you doing here ?")


@login_required()
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def admin_user_send_mail(request, user_id):
    """Send an email to a user."""
    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            send_mail(
                form.cleaned_data['subject'],
                form.cleaned_data['message'],
                'openstudyroom@gmail.com',
                [user.get_primary_email().email, form.cleaned_data['copy_to']],
                fail_silently=False,
            )
            message = "Successfully sent an email to " + str(user)
            messages.success(request, message)
            return HttpResponseRedirect(reverse('league:admin'))
    else:
        form = EmailForm()
        context = {'form': form, 'user': user}
        return render(request, 'league/admin/user_send_mail.html', context)


def discord_redirect(request):
    """loads discord invite url from discord_url_file and redirects the user if he passes the tests."""
    if request.user.is_authenticated and request.user.user_is_league_member:
        with open(discord_url_file) as f:
            disc_url = f.read().strip()
        return HttpResponseRedirect(disc_url.replace('\n', ''))
    else:
        message = "OSR discord server is for members only."
        messages.success(request, message)
        return HttpResponseRedirect('/')


@login_required()
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
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
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def admin_users_list(request, event_id=None, division_id=None):
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
@user_passes_test(is_league_member, login_url="/", redirect_field_name=None)
def scrap_list_up(request, profile_id):
    """ Set user profile p_status to 2 so this user will be checked soon"""
    profile = get_object_or_404(Profile, pk=profile_id)
    if profile.p_status == 2:
        message = str(profile.user) + ' will already be scraped with hight priority'
        messages.success(request, message)
        return HttpResponseRedirect(reverse('league:scrap_list'))
    if profile.user == request.user or request.user.user_is_league_admin():
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


@login_required()
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def create_all_profiles(request):
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


@login_required()
@user_passes_test(is_league_admin, login_url="/", redirect_field_name=None)
def update_all_sgf(request):
    if request.method == 'POST':
        form = ActionForm(request.POST)
        if form.is_valid():
            games = Game.objects.all()
            for game in games:
                sgf = game.sgf
                sgf.black = game.black.user
                sgf.white = game.white.user
                sgf.winner = game.winner.user
                sgf.divisions.add(game.white.division)
                sgf.events.add(game.event)
                sgf.save()

            message = "Successfully updated " + str(games.count()) + " sgfs."
            messages.success(request, message)
            return HttpResponseRedirect(reverse('league:admin'))
        else:
            message = "Something went wrong (form is not valid)"
            messages.success(request, message)
            return HttpResponseRedirect(reverse('league:admin'))
    else:
        return render(request, 'league/admin/update_all_sgf.html')
