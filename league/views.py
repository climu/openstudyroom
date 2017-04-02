from django.shortcuts import get_object_or_404, render
from django.template import loader
from django.db import models
from django.http import HttpResponse, HttpResponseRedirect,Http404
from .models import Sgf,LeaguePlayer,User,LeagueEvent,Division,Game,Registry, User, is_league_admin, is_league_member
from .forms import  SgfAdminForm,ActionForm,LeaguePopulateForm,UploadFileForm,DivisionForm,LeagueEventForm,EmailForm
import datetime
from django.http import Http404
from django.core.urlresolvers import reverse
from django.core.files import File
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django import forms
from django.contrib.auth.models import  Group
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from collections import OrderedDict
from . import utils
from django.core.mail import send_mail
from django.views.generic.edit import UpdateView
from django.views.generic.edit import CreateView
import json

discord_url_file = "/etc/discord_url.txt"

def scraper():
	#the big scraper thing
	# To prevent overrequestion kgs, do one of the 3 actions only:
	#1 check time since get from kgs
	#2 look for some sgfs that analyse and maybe pulled as games
	#3 check a player

	event=Registry.get_primary_event()
	#1check time since get from kgs
	now=datetime.datetime.now().replace(tzinfo=None)
	last_kgs=Registry.get_time_kgs().replace(tzinfo=None)
	delta=now-last_kgs
	delta_sec = delta.total_seconds()
	kgs_delay = Registry.get_kgs_delay()
	if delta_sec < kgs_delay: #we can't scrape yet
		out='too soon'
		return out
	#2 look for some sgfs that we analyse and maybe record as games
	sgfs=Sgf.objects.filter(p_status=2)
	if len(sgfs)==0 :
		sgfs=Sgf.objects.filter(p_status=1)
	if len(sgfs)>0 :
		sgf = sgfs[0]
		#parse the sgf datas to populate the rows
		sgf = sgf.parse()
		#if the sgf doesn't have a result (unfinished game) we just delete it
		if sgf.result == '?':
			sgf.delete()
		else:
			sgf = sgf.check_validity()
			sgf.save()
			if sgf.league_valid:
				Game.create_game(sgf)
		out = sgf
	#3 no games to scrap let's check a player
	else :
		players=LeaguePlayer.objects.filter(event=event)
		#if everyone has been checked.
		if not(players.filter(p_status__gt =0).exists()):
			players.update(p_status=1)
		if players.filter(p_status =2).exists():
			player=players.filter(p_status = 2)[0]
			player.check_player()
			out=player
		else:
			player = players.filter(p_status = 1)[0]
			player.check_player()
		out=player
	Registry.set_time_kgs(now)
	return out

def scraper_view(request):
	out=scraper()
	return HttpResponse(out)

def sgf(request,sgf_id):
	sgf=get_object_or_404(Sgf,pk = sgf_id)
	response = HttpResponse(sgf.sgf_text, content_type='application/octet-stream')
	response['Content-Disposition'] = 'attachment; filename="'+ sgf.wplayer + '-' + sgf.bplayer + '-'+ sgf.date.strftime('%m/%d/%Y')+'.sgf"'
	return response

def games(request,event_id=None,game_id=None):
	context = {}
	if game_id != None:
		game = get_object_or_404(Game,pk = game_id)
		context.update({'game':game})

	if event_id == None:
		games=Game.objects.all().order_by('-sgf__date')
		context.update({'games': games})
		template = loader.get_template('league/archives_games.html')

	else:
		event = get_object_or_404(LeagueEvent,pk=event_id)
		close = event.is_close()
		games=Game.objects.filter(white__event=event).order_by('-sgf__date')
		template = loader.get_template('league/games.html')
		context.update( {
			'games': games,
			'event':event,
			'close':close,
			})
	return HttpResponse(template.render(context, request))



def results(request,event_id=None,division_id=None):
	if event_id == None:
		event = Registry.get_primary_event()
	else:
		event=get_object_or_404(LeagueEvent,pk=event_id)
	if division_id == None:
		division = Division.objects.filter(league_event=event).first()
	else:
		division = get_object_or_404(Division,pk=division_id)
	results = division.get_results()
	template = loader.get_template('league/results.html')
	players = LeaguePlayer.objects.filter(division=division).order_by('-score')
	close = event.is_close()
	context = {
		'players':players,
		'event':event,
		'division':division,
		'close' : close,
		'results' :results,
		}
	return HttpResponse(template.render(context, request))



def archives(request):
		primary_event = Registry.get_primary_event()
		events = LeagueEvent.objects.all()

		context = {
		'events':events,
		}
		template = loader.get_template('league/archive.html')
		return HttpResponse(template.render(context, request))

def event(request,event_id=None,division_id=None,):
	if event_id == None:
		event = Registry.get_primary_event()
	else:
		event=get_object_or_404(LeagueEvent,pk=event_id)
	if division_id == None:
		division = Division.objects.filter(league_event=event).first()
	else:
		division = get_object_or_404(Division,pk=division_id)
	close = event.is_close()
	context = {
		'event':event,
		'close':close,

		}
	template = loader.get_template('league/event.html')
	return HttpResponse(template.render(context, request))

def players(request,event_id=None,division_id=None):
	#if no event is provided, we show all the league members
	if event_id == None:
		users=User.objects.filter(groups__name='league_member')
		context = {
			'users':users,
		}
		template = loader.get_template('league/archives_players.html')
	else:
		event=get_object_or_404(LeagueEvent,pk=event_id)
		#if no division is provided, we show all players from this event
		if division_id == None:
			players = LeaguePlayer.objects.filter(event=event).order_by('-score')
			divisions=event.division_set.all()
		else:
			division = get_object_or_404(Division,pk=division_id)
			divisions = [division]
			players = LeaguePlayer.objects.filter(event=event,division = division).order_by('-p_score')
		close = event.is_close
		context = {
			'event':event,
			'players':players,
			'close' : close,
			'divisions':divisions
		}
		template = loader.get_template('league/players.html')
	return HttpResponse(template.render(context, request))

def account(request,user_name=None):
	#This view does many things:
	# if url ask for a user( /league/user/climu) display that user profile.
	# if none, we check if user is auth and, if so,  we display his own profile.
	# In the template, we will display a join button only if user is auth and request.user == user
	primary_event = Registry.get_primary_event()
	if user_name == None: # if no user provide  by url, we check if user is auth and if so display hi own profile
		if request.user.is_authenticated :
			 user=request.user
		else:
			return HttpResponseRedirect('/')# maybe a view with a list of all our users might be cool redirection here
	else:
		#user = get_object_or_404(User,username = user_name)
		user= User.objects.get(username=user_name)

	if not is_league_member(user): return HttpResponseRedirect('/')

	if request.method == 'POST':
		if request.user.is_authenticated() and user == request.user:

			form=ActionForm(request.POST)
			if form.is_valid():
				if form.cleaned_data['action'] == 'join':
					division = Division.objects.filter(league_event = primary_event).order_by('-order').first()
					user.join_event(primary_event,division)
					message ="Welcome in " + division.name +" ! You can start playing right now."
					messages.success(request,message)
					return HttpResponseRedirect(reverse('league:league_account'))

	else:
		players = user.leagueplayer_set.order_by('-pk')
		games = Game.objects.filter(Q(black__in = players)|Q(white__in = players))
		if user.is_in_primary_event():
			active_player = user.get_primary_event_player()
			opponents = LeaguePlayer.objects.filter(division=active_player.division).order_by('-score')
		else:
			active_player = False
			opponents = []
		context = {
		'players' : players,
		'primary_event':primary_event,
		'games' : games,
		'active_player' : active_player,
		'opponents' : opponents,
		'user' :user,
		}
		template = loader.get_template('league/account.html')
		return HttpResponse(template.render(context, request))

def game_api(request,game_id):
	''' will return a json containing:
	'infos': players, date, league, group, permalink, download link.
	'sgf': sgf datas as plain text string
	'''
	game = get_object_or_404(Game, pk= game_id)
	event = game.event
	division = game.white.division
	sgf = game.sgf
	html=loader.render_to_string("league/includes/game_info.html",{'game':game})
	data = {}
	data['sgf'] = sgf.sgf_text.replace(';B[]',"").replace(';W[]',"")
	data['permalink'] = '/league/games/'+ str(game.pk)
	data['game_infos'] = html
	data['white'] = str(game.white)
	data['black'] = str(game.black)

	return HttpResponse(json.dumps(data), content_type = "application/json")


@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def admin_sgf_list(request):
	sgfs=Sgf.objects.all()
	context={'sgfs':sgfs}
	return render(request,'league/admin/sgf_list.html', context)



@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def handle_upload_sgf(request):
	if request.method =='POST':
		form = UploadFileForm(request.POST, request.FILES)
		if form.is_valid():
			file=request.FILES['file']
			sgf_data=file.read().decode('UTF-8')
			request.session['sgf_data'] = sgf_data
			return HttpResponseRedirect(reverse('league:upload_sgf'))
		else :raise Http404("What are you doing here ?")
	else :raise Http404("What are you doing here ?")

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def create_sgf(request):
	if request.method =='POST':
		form = SgfAdminForm(request.POST)
		if form.is_valid():
			sgf=Sgf()
			sgf.sgf_text = form.cleaned_data['sgf']
			sgf.p_status = 2
			sgf=sgf.parse()
			sgf = sgf.check_validity()
			if sgf.league_valid:
				sgf.save()
				Game.create_game(sgf)
				message =" Succesfully created a sgf and a league game"
				messages.success(request,message)
			else:
				message =" the sgf didn't seems to pass the tests"
				messages.success(request,message)
	return HttpResponseRedirect(reverse('league:admin'))


@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def upload_sgf(request):
	if request.method =='POST':
		form = SgfAdminForm(request.POST)
		if form.is_valid():
			sgf=Sgf()
			sgf.sgf_text = form.cleaned_data['sgf']
			sgf.p_status = 2
			sgf=sgf.parse()
			sgf = sgf.check_validity()
			form = SgfAdminForm(initial={'sgf':sgf.sgf_text})

			context = {
			'sgf':sgf,
			'form': form,
			}
			template = loader.get_template('league/admin/upload_sgf.html')
			return HttpResponse(template.render(context, request))
	else:
		if 'sgf_data' in request.session:
			if request.session['sgf_data'] == None: raise Http404("What are you doing here ?")
			sgf=Sgf()
			sgf.sgf_text = request.session['sgf_data']
			request.session['sgf_data']=None
			sgf.p_status = 2
			sgf=sgf.parse()
			sgf = sgf.check_validity()
			form = SgfAdminForm(initial={'sgf':sgf.sgf_text})
			context = {
			'sgf':sgf,
			'form': form,
			}
			template = loader.get_template('league/admin/upload_sgf.html')
			return HttpResponse(template.render(context, request))
		else : raise Http404("What are you doing here ?")

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def admin_delete_game(request,game_id):
	''' delete a game and add the message " deleted by admin to the sgf"'''
	game = get_object_or_404(Game,pk = game_id)
	if request.method == 'POST':
		form=ActionForm(request.POST)
		if form.is_valid():
			if form.cleaned_data['action'] == 'delete_game':
				sgf=game.sgf
				sgf.message += ";deleted by admin ("+ str(game.pk) +")"
				sgf.save()
				game.delete()
				form = SgfAdminForm(initial={'sgf':sgf.sgf_text,'url':sgf.urlto})
				context = {
				'sgf':sgf,
				'form': form,
				}
				message ="The game " + str(game) + "has been deleted"
				messages.success(request,message)
				return HttpResponseRedirect(reverse('league:edit_sgf',args=[sgf.pk]))
	raise Http404("What are you doing here ?")

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def admin_create_game(request,sgf_id):
	sgf = get_object_or_404(Sgf,pk=sgf_id)
	if request.method =='POST':
		form = ActionForm(request.POST)
		if form.is_valid():
			sgf = sgf.check_validity()
			if sgf.league_valid:
				if Game.create_game(sgf): message='Successfully created the game ' + sgf.wplayer + ' vs ' + sgf.bplayer +' !'
				else: message="We coudln't create a league game for this sgf"
			else:
				message="The sgf is not valid so we can't create a game"
		else :raise Http404("What are you doing here ?")
	messages.success(request,message)
	return HttpResponseRedirect(reverse('league:edit_sgf',args=[sgf.pk]))

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def admin_save_sgf(request,sgf_id):
	sgf = get_object_or_404(Sgf, pk=sgf_id)
	if request.method == 'POST':
		form = SgfAdminForm(request.POST)
		if form.is_valid():
			sgf.sgf_text = form.cleaned_data['sgf']
			sgf.urlto = form.cleaned_data['url']
			sgf.p_status = 2
			sgf = sgf.parse()
			sgf = sgf.check_validity()
			sgf.save()
	message = 'successfully saved the sgf in the db'
	messages.success(request,message)
	return HttpResponseRedirect(reverse('league:edit_sgf',args=[sgf.pk]))

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def admin_delete_sgf(request,sgf_id):
	sgf = get_object_or_404(Sgf, pk=sgf_id)
	if request.method == 'POST':
		message = 'successfully deleted the sgf ' + str(sgf)
		messages.success(request,message)
		sgf.delete()
		return HttpResponseRedirect(reverse('league:admin'))
	else:raise Http404("What are you doing here ?")

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def admin_edit_sgf(request,sgf_id):
	sgf = get_object_or_404(Sgf, pk=sgf_id)
	if request.method == 'POST':
		form = SgfAdminForm(request.POST)
		if form.is_valid():
			sgf.sgf_text = form.cleaned_data['sgf']
			sgf.urlto = form.cleaned_data['url']
			sgf.p_status = 2
			sgf = sgf.parse()
			sgf = sgf.check_validity()
			form = SgfAdminForm(initial={'sgf':sgf.sgf_text, 'url':sgf.urlto})
			context = {
			'sgf':sgf,
			'form': form,
			'preview': True
			}
			template = loader.get_template('league/admin/sgf_edit.html')
			return HttpResponse(template.render(context, request))
	else:
		form = SgfAdminForm(initial={'sgf':sgf.sgf_text, 'url':sgf.urlto})
		context={
		'form' : form,
		'sgf' : sgf,
		'preview': False
		}
		return render(request,'league/admin/sgf_edit.html', context)



@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def admin(request):
	event = Registry.get_primary_event()
	if request.method =='POST':
		form = ActionForm(request.POST)
		if form.is_valid():
			if form.cleaned_data['action'] == "welcome_new_user":
				user=User.objects.get(pk=form.cleaned_data['user_id'])
				user.groups.clear()
				group = Group.objects.get(name='league_member')
				user.groups.add(group)
				division=Division.objects.filter(league_event=event).last()
				user.join_event(event,division)
				message =" You moved " + user.username + "from new user to league member"
				messages.success(request,message)
				return HttpResponseRedirect(reverse('league:admin'))
			if form.cleaned_data['action'] == "delete_new_user":
					user=User.objects.get(pk=form.cleaned_data['user_id'])
					user.delete()
					message =" You just deleted " + user.username + "! Bye bye " + user.username +"."
					messages.success(request,message)
					return HttpResponseRedirect(reverse('league:admin'))
	else:
		sgfs = Sgf.objects.filter(league_valid=False,p_status = 0)
		new_users=User.objects.filter(groups__name='new_user')
		form = UploadFileForm()
		context={
		'sgfs' : sgfs,
		'new_users': new_users,
		'form':form,
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
	initial = { 'begin_time': datetime.datetime.now(),
				'end_time': datetime.datetime.now() }


	def test_func(self):
		return self.request.user.is_authenticated() and self.request.user.user_is_league_admin()

	def get_login_url(self):
		return '/'


@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name=None)
def admin_events(request, event_id=None):
	events = LeagueEvent.objects.all().order_by("-begin_time")
	primary_event = Registry.get_primary_event().pk
	edit_event = -1
	if not event_id is None:
		edit_event = get_object_or_404(LeagueEvent, pk=event_id)

	template = loader.get_template('league/admin/events.html')
	context = { 'events': events,
				'edit_event': edit_event,
				'primary_pk': primary_event}
	return HttpResponse(template.render(context, request))

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name=None)
def admin_events_set_primary(request, event_id):
	event = get_object_or_404(LeagueEvent,pk=event_id)
	if request.method =='POST':
		form = ActionForm(request.POST)
		if form.is_valid():
			if form.cleaned_data['action'] == "set_primary":
				r=Registry.objects.get(pk=1)
				r.primary_event = event
				r.save()
				message ="Changed primary event to \"{}\"".format(r.primary_event.name)
				messages.success(request,message)
				return HttpResponseRedirect(reverse('league:admin_events'))
	raise Http404("What are you doing here ?")

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def admin_delete_division(request,division_id):
	division = get_object_or_404(Division, pk=division_id)
	event = division.league_event
	if request.method =='POST':
		form = ActionForm(request.POST)
		if form.is_valid():
			if form.cleaned_data['action'] == "delete_division":
				nb_players= division.number_players()
				if nb_players >0:
					message="You just deleted the division" + str(division) +" and the " + str(nb_players) +" players in it."
				else:
					message="You just deleted the empty division" + str(division) +"."
				division.delete()
				messages.success(request,message)
				return HttpResponseRedirect(reverse('league:admin_events_update',kwargs={'pk':event.pk}))

	raise Http404("What are you doing here ?")

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def admin_events_delete(request,event_id):
	event = get_object_or_404(LeagueEvent, pk=event_id)
	if not request.method == 'POST':
		raise Http404("What are you doing here ?")

	form = ActionForm(request.POST)
	if not form.is_valid():
		raise Http404("What are you doing here ? (Token Error)")

	message = 'Successfully deleted the event ' + str(event)
	messages.success(request,message)
	event.delete()
	return HttpResponseRedirect(reverse('league:admin_events'))

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def admin_create_division(request,event_id):
	event=get_object_or_404(LeagueEvent,pk=event_id)
	if request.method =='POST':
		form = DivisionForm(request.POST)
		if form.is_valid():
			division = form.save(commit=False)
			division.league_event = event
			division.order = event.last_division_order() +1
			division.save()
		return HttpResponseRedirect(reverse('league:admin_events_update',kwargs={'pk':event_id}))
	else : raise Http404("What are you doing here ?")

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name=None)
def admin_rename_division(request,division_id):
	division=get_object_or_404(Division,pk=division_id)
	event = division.league_event

	if request.method =='POST':
		form = DivisionForm(request.POST)
		if form.is_valid():
			message = "You renamed " + str(division) + " to " + form.cleaned_data['name']
			division.name=form.cleaned_data['name']
			division.save()
			messages.success(request,message)
			return HttpResponseRedirect(reverse('league:admin_events_update',kwargs={'pk':event.pk}))
	raise Http404("What are you doing here ?")

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name=None)
def admin_division_up_down(request,division_id):
	'''changing division order. Note that if admin have deleted a division, the order change might not be just +-1'''
	division_1 = get_object_or_404(Division,pk=division_id)
	event = division_1.league_event
	if request.method =='POST':
		form = ActionForm(request.POST)
		if form.is_valid():
			if form.cleaned_data['action'] == "division_up" and not division_1.is_first():
				order=division_1.order
				while not event.division_set.exclude(pk=division_1.pk).filter(order=order).exists():
					order -= 1
				division_2 = Division.objects.get(league_event=division_1.league_event,order=order)
				order_2 = division_1.order
				division_2.order = -1
				division_2.save()
				division_1.order = order
				division_1.save()
				division_2.order = order_2
				division_2.save()
			if form.cleaned_data['action'] == "division_down" and not division_1.is_last():
				order=division_1.order
				while not event.division_set.exclude(pk=division_1.pk).filter(order=order).exists():
					order += 1
				division_2 = Division.objects.get(league_event=division_1.league_event,order=order)
				order_2 = division_1.order
				division_2.order = -1
				division_2.save()
				division_1.order = order
				division_1.save()
				division_2.order = order_2
				division_2.save()
			return HttpResponseRedirect(reverse('league:admin_events_update',kwargs={'pk':event.pk}))
	raise Http404("What are you doing here ?")

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def populate(request,to_event_id,from_event_id=None):
	'''
	A view that helps admin to do populate at the end of the month.
	It displays users from primary_event and let the admin choose to which division they will be in next event.
	This view can perform a preview loading data from the form. Actual db populating happen in proceed_populate view

	'''
	to_event = get_object_or_404(LeagueEvent,pk=to_event_id)
	new_players= OrderedDict()
	for division in to_event.get_divisions():
		new_players[division.name]=[]

	if request.method == 'POST':
		if from_event_id is None:
			 raise Http404("What are you doing here ?")
		else: from_event = get_object_or_404(LeagueEvent,pk = from_event_id)
		form = LeaguePopulateForm(from_event,to_event,request.POST)
		if form.is_valid():
			for player in from_event.get_players():
				if player.is_active():
					new_division = Division.objects.get(pk=form.cleaned_data['player_'+str(player.pk)])
					new_player = LeaguePlayer(user=player.user,event = to_event,kgs_username = player.kgs_username,division=new_division)
					new_player.previous_division=player.division
					new_players[new_division.name].append(new_player)
			#Admin have a preview so we are sure form is not dumber than the admin. We will display the save button in template
			preview=True
	else:
		if 'from_event' in request.GET :
			from_event = get_object_or_404(LeagueEvent,pk=request.GET['from_event'])
		else:
			raise Http404("What are you doing here ?")
		form = LeaguePopulateForm(from_event,to_event)
		# Having preview at false prevent the save button to be displayed in tempalte
		preview=False

	context = {
			'from_event' : from_event,
			'to_event' : to_event,
			'form' : form,
			'new_players' : new_players,
			'preview' : preview,
		}
	template = loader.get_template('league/admin/populate.html')
	return HttpResponse(template.render(context, request))

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def proceed_populate(request,from_event_id,to_event_id):
	''' Here we actually populate the db with the form from populate view.
	We assume the admin have seen the new events structure in a preview before being here.
	'''

	# populate view should have the admin select this event and sending this here in the form.

	to_event = get_object_or_404(LeagueEvent,pk=to_event_id)
	from_event = get_object_or_404(LeagueEvent,pk=from_event_id)
	if request.method == 'POST':
		form = LeaguePopulateForm(from_event,to_event,request.POST)
		if form.is_valid():
			n=0
			for player in from_event.get_players():
				if player.is_active():
						n+=1
						new_division = Division.objects.get(pk=form.cleaned_data['player_'+str(player.pk)])
						new_player = LeaguePlayer.objects.create(user=player.user,event = to_event,kgs_username = player.kgs_username,division=new_division)
		message ="The new "+ to_event.name +" was populated with "+ str(n) +" players."
		messages.success(request,message)
		return HttpResponseRedirect(reverse('league:admin_events' ))
	else:
		raise Http404("What are you doing here ?")

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def admin_user_send_mail(request,user_id):
	'''
	send an email to a user
	'''
	user = get_object_or_404(User,pk=user_id)

	if request.method == 'POST':
		form = EmailForm(request.POST)
		if form.is_valid():
			send_mail(
	    	form.cleaned_data['subject'],
			form.cleaned_data['message'],
			'openstudyroom@gmail.com',
			[user.get_primary_email().email,form.cleaned_data['copy_to']],
			fail_silently=False,
			)
			message="Successfully sent an email to "+ str(user)
			messages.success(request,message)
			return HttpResponseRedirect(reverse('league:admin' ))
	else:
		form = EmailForm()
		context = {'form':form,'user':user}
		return render(request,'league/admin/user_send_mail.html',context)

def discord_redirect(request):
	'''loads discord invite url from discord_url_file and redirects the user if he passes the tests.'''
	if request.user.is_authenticated and request.user.user_is_league_member:
		with open(discord_url_file) as f:
			disc_url = f.read().strip()
		return HttpResponseRedirect(disc_url.replace('\n', ''))
	else:
		message ="OSR discord server is for members only."
		messages.success(request,message)
		return HttpResponseRedirect('/')

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def update_all_sgf(request):
	'''
	Reparse all sgf from db. This can be usefull after adding a new field to sgf models.
	We just display a confirmation page with a warning if no post request.
	For now, we will just update the check_code field.
	Latter, we might add a select form to select what field(s) we want update
	'''
	if request.method == 'POST':
		form = ActionForm(request.POST)
		if form.is_valid():
			sgfs= Sgf.objects.all()
			for sgf in sgfs:
				sgf_prop=utils.parse_sgf_string(sgf.sgf_text)
				sgf.check_code=sgf_prop['check_code']
				sgf.save()
			message ="Successfully updated " + str(sgfs.count()) + " sgfs."
			messages.success(request,message)
			return HttpResponseRedirect(reverse('league:admin'))
		else:
			message ="Something went wrong (form is not valid)"
			messages.success(request,message)
			return HttpResponseRedirect(reverse('league:admin'))
	else:

		return render(request,'league/admin/update_all_sgf.html')


@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def admin_users_list(request,event_id=None,division_id=None):
	event = None
	division = None
	if event_id is None:
		users = User.objects.all()
	else:
		event = get_object_or_404(LeagueEvent,pk=event_id)
		if division_id is None:
			players = event.leagueplayer_set.all()
			users = User.objects.filter(leagueplayer__in  =players)
		else:
			division = get_object_or_404(Division,pk=division_id)
			players = division.leagueplayer_set.all()
			users = User.objects.filter(leagueplayer__in  =players)
	context = {
	'users': users,
	'event': event,
	'division': division,
	}
	return render(request,'league/admin/users.html',context)

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def scrap_list(request):
	event = Registry.get_primary_event()
	players = event.leagueplayer_set.all().order_by('-p_status')
	context = {
	'event':event,
	'players':players
	}
	return render(request,'league/scrap_list.html',context)

@login_required()
@user_passes_test(is_league_member,login_url="/",redirect_field_name = None)
def scrap_list_up(request,player_id):
	''' Set player p_status to 2 so this player will be checked soon'''
	player = get_object_or_404(LeaguePlayer,pk=player_id)
	if player.p_status == 2:
		message = str(player) + ' will already be scraped with hight priority'
		messages.success(request,message)
		return HttpResponseRedirect(reverse('league:scrap_list'))

	if request.method == 'POST':
		form = ActionForm (request.POST)
		if form.is_valid():
			if form.cleaned_data['action'] == 'p_status_up':
				player.p_status = 2
				player.save()
				message = 'You just moved ' + str(player) + ' up the scrap list'
				messages.success(request,message)
				return HttpResponseRedirect(reverse('league:scrap_list'))
	raise Http404("What are you doing here ?")
