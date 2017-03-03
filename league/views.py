from django.shortcuts import get_object_or_404, render
from django.template import loader
from django.db import models
from django.http import HttpResponse, HttpResponseRedirect,Http404
from .models import Sgf,LeaguePlayer,User,LeagueEvent,Division,Game,Registry, User, is_league_admin, is_league_member
from .forms import  SgfAdminForm,ActionForm,LeagueRolloverForm,UploadFileForm
import datetime
from django.http import Http404
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django import forms
from django.contrib.auth.models import  Group
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from collections import OrderedDict
from . import utils





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
		return
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
			player=player.filter(p_status = 2)[0]
			player.check_player()
		else:
			player = players.filter(p_status = 1)[0]
			player.check_player()
		out=player
	Registry.set_time_kgs(now)
	return

def scraper_view(request):
	scraper()
	return httpResponse('scraped')

def games(request,event_id=None):
	if event_id == None:
		games=Game.objects.all()
		context = {
			'games': games,
				}
		template = loader.get_template('league/archives_games.html')

	else:
		event = get_object_or_404(LeagueEvent,pk=event_id)
		close = event.end_time.replace(tzinfo=None) < datetime.datetime.now().replace(tzinfo=None)
		games=Game.objects.filter(white__event=event)
		template = loader.get_template('league/games.html')
		context = {
			'games': games,
			'event':event,
			'close':close,
			}
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
	template = loader.get_template('league/results.html')
	players=LeaguePlayer.objects.filter(division=division).order_by('-score')
	close = event.end_time.replace(tzinfo=None) < datetime.datetime.now().replace(tzinfo=None)
	context = {
		'players':players,
		'event':event,
		'division':division,
		'close' : close,
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
	close = event.end_time.replace(tzinfo=None) < datetime.datetime.now().replace(tzinfo=None)
	context = {
		'event':event,
		'close':close,

		}
	template = loader.get_template('league/event.html')
	return HttpResponse(template.render(context, request))

def players(request,event_id=None,division_id=None):
	if event_id == None:
		users=User.objects.filter(groups__name='league_member')
		context = {
			'users':users,
		}
		template = loader.get_template('league/archives_players.html')
	else:
		event=get_object_or_404(LeagueEvent,pk=event_id)
		if division_id == None:
			players = LeaguePlayer.objects.filter(event=event).order_by('-score')
		else:
			division = get_object_or_404(Division,pk=division_id)
			players = LeaguePlayer.objects.filter(event=event,division = division)
		close = event.end_time.replace(tzinfo=None) < datetime.datetime.now().replace(tzinfo=None)
		context = {
			'event':event,
			'players':players,
			'close' : close,
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
			template = loader.get_template('league/upload_sgf.html')
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
			template = loader.get_template('league/upload_sgf.html')
			return HttpResponse(template.render(context, request))
		else : raise Http404("What are you doing here ?")

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def sgf_view(request,sgf_id):
	sgf = get_object_or_404(Sgf, pk=sgf_id)
	if request.method == 'POST':
		form = SgfAdminForm(request.POST)
		if form.is_valid():
			sgf.sgf_text = form.cleaned_data['sgf']
			sgf.p_status = 2
			sgf.save()
			message =" You just modified the sgf " + sgf.wplayer + " Vs "+ sgf.bplayer
			messages.success(request,message)
		return HttpResponseRedirect(reverse('league:admin'))
	else:
		form = SgfAdminForm(initial={'sgf':sgf.sgf_text})
		context={
		'form' : form,
		'sgf' : sgf,
		}
		return render(request,'league/sgf.html', context)


@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def admin(request):
	event = Registry.get_primary_event()
	if request.method =='POST':
		form = ActionForm(request.POST)
		if form.is_valid():
			print(form.cleaned_data['action'])
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
		template = loader.get_template('league/admin.html')
		return HttpResponse(template.render(context, request))





@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def rollover(request):
	from_event = Registry.get_primary_event()
	to_event = LeagueEvent.objects.filter(pk=from_event.pk+1).first()

	if to_event == None:
		message =" You must create a new event and his divisions before processing rollover."
		messages.success(request,message)
		return HttpResponseRedirect(reverse('league:admin'))

	if to_event.number_players()>0:
		message = "Something strange: you tryed to rollover to a league with players already in it"
		messages.success(request,message)
		return HttpResponseRedirect(reverse('league:admin'))

	new_players= OrderedDict()
	for division in to_event.get_divisions():
		new_players[division.name]=[]

	if request.method == 'POST':
		form = LeagueRolloverForm(from_event,to_event,request.POST)
		if form.is_valid():
			for player in from_event.get_players():
				if player.is_active():
					new_division = Division.objects.get(pk=form.cleaned_data['player_'+str(player.pk)])
					new_player = LeaguePlayer(user=player.user,event = to_event,kgs_username = player.kgs_username,division=new_division)
					new_player.previous_division=player.division
					new_players[new_division.name].append(new_player)
			preview=True
	else:
		form = LeagueRolloverForm(from_event,to_event)
		preview=False

	context = {
			'from_event' : from_event,
			'to_event' : to_event,
			'form' : form,
			'new_players' : new_players,
			'preview' : preview,
		}
	template = loader.get_template('league/rollover.html')
	return HttpResponse(template.render(context, request))

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def proceed_rollover(request):
	from_event = Registry.get_primary_event()
	to_event = LeagueEvent.objects.filter(pk=from_event.pk+1).first()
	if request.method == 'POST':
		form = LeagueRolloverForm(from_event,to_event,request.POST)
		if form.is_valid():
			n=0
			for player in from_event.get_players():
				if player.is_active():
						n+=1
						new_division = Division.objects.get(pk=form.cleaned_data['player_'+str(player.pk)])
						new_player = LeaguePlayer.objects.create(user=player.user,event = to_event,kgs_username = player.kgs_username,division=new_division)
		message ="The new "+ to_event.name +" was populated with "+ str(n) +" players."
		messages.success(request,message)
		return HttpResponseRedirect(reverse('league:admin'))
	else:
		raise Http404("What are you doing here ?")

@login_required()
@user_passes_test(is_league_admin,login_url="/",redirect_field_name = None)
def send_user_mail(request):
	send_mail(
    	'Subject here',
    	'Here is the message.',
    	'from@example.com',
    	['climmu@gmail.com'],
    	fail_silently=False,
		)
	return HttpResponse('sent')
