from django.db import models
from django.utils import timezone
import datetime
from . import utils
import requests
from django.contrib.auth.models import AbstractUser



# Create your models here.
class LeagueEvent(models.Model):
	begin_time = models.DateTimeField(blank=True)
	end_time =  models.DateTimeField(blank=True)
	name = models.TextField(max_length=20)
	nb_matchs = models.SmallIntegerField(default=2)
	ppwin = models.DecimalField(default=1.5, max_digits=2, decimal_places=1)
	pploss = models.DecimalField(default=0.5, max_digits=2, decimal_places=1)
	min_matchs = models.SmallIntegerField(default=1)
	class Meta:
		ordering = ['-begin_time']

	def __str__(self):
		return self.name

	def get_year(self):
		return self.begin_time.year

	def get_month(self):
		return self.begin_time.month

	def number_players(self):
		return self.leagueplayer_set.count()

	def number_games(self):
		return self.game_set.count()

	def number_divisions(self):
		return self.division_set.count()

	def possible_games(self):
		divisions=self.division_set.all()
		n=0
		for division in divisions:
			n+=division.possible_games()
		return n

	def percent_game_played(self):
		p= self.possible_games()
		if p == 0:
			n=100
		else:
			n= round(float(self.number_games()) / float(self.possible_games()) * 100,2)
		return n

	def get_divisions(self):
		return self.division_set.all()

	def get_players(self):
		return self.leagueplayer_set.all()

	def number_actives_players(self):
		#not proud of this method. It works thought
		n=0
		for player in self.get_players():
			if player.nb_games()>=self.min_matchs: n+=1
		return n

	def number_inactives_players(self):
		return (self.number_players()-self.number_actives_players())






class Registry(models.Model):
	# this class should only have one instance.
	# Anyway, other than pk=0 won't be use
	# Maybe there is a better way to achieve such... let me know
	#EDIT: Breaking news !!! django-setting would do it just fine. Maybe latter...

	primary_event = models.ForeignKey(LeagueEvent)
	time_kgs = models.DateTimeField(default=datetime.datetime.now,blank=True) #last time we request kgs
	kgs_delay = models.SmallIntegerField(default=19) #time between 2 kgs get

	@staticmethod
	def get_primary_event():
		r=Registry.objects.get(pk=1)
		return r.primary_event

	@staticmethod
	def get_time_kgs():
		r=Registry.objects.get(pk=1)
		return r.time_kgs

	@staticmethod
	def get_kgs_delay():
		r=Registry.objects.get(pk=1)
		return r.kgs_delay

	@staticmethod
	def set_time_kgs(time):
		r=Registry.objects.get(pk=1)
		r.time_kgs = time
		r.save()


class Sgf(models.Model):
	#when a sgf is added, we 1st add just the urlto then we add the rest with parse
	# this is to prevent many kgs get request in short time
	sgf_text = models.TextField(default='sgf')
	urlto = models.URLField(default='http://')
	wplayer = models.CharField(max_length=200,default='?')
	bplayer = models.CharField(max_length=200,default='?')
	place = models.CharField(max_length=200,default='?')
	result = models.CharField(max_length=200,default='?')
	league_valid = models.BooleanField(default=False)
	date =  models.DateTimeField(default=datetime.datetime.now,blank=True)
	board_size = models.SmallIntegerField(default=19)
	handicap = models.SmallIntegerField(default=0)
	komi = models.DecimalField(default=6.5, max_digits=5, decimal_places=2)
	byo = models.CharField(max_length=20,default='sgf')
	time = models.SmallIntegerField(default=19)
	game_type = models.CharField(max_length=20,default='Free')
	message = models.CharField(max_length=100,default='nothing',blank=True)
	number_moves = models.SmallIntegerField(default=100)
	p_status = models.SmallIntegerField(default=1)
	check_code = models.CharField(max_length=100,default='nothing',blank=True)
	# status of the sgf:0 already checked
	#					1 require checking, sgf added from kgs archive link
	#					2 require checking with priority,sgf added/changed by admin

	def __str__(self):
		return self.wplayer + ' vs ' + self.bplayer


	def parse(self):
		#parse one sgf :
		#check the p_status, and populate the rows
		if self.p_status == 0:
			return
		if self.p_status == 1: # we only have the urlto and need a kgs request
			r = requests.get(self.urlto)
			self.sgf_text = r.text
		prop = utils.parse_sgf_string(self.sgf_text)
		#prop['time'] = int(prop['time'])
		for k, v in prop.items(): setattr(self, k, v)
		self.p_status=0
		return self



	def check_validity(self):
		# check sgf validity: oponents in same Division, tag , timesetting,not a review
		# We will reperform check on players division because a user could have upload a sgf by hand
		# hence such a sgf wouldn't have been check during check_player
		#flag it
		b = True
		m = ''
		if self.game_type == 'review': (b,m) = (False,m+' review gametype')
		if self.sgf_text.find('#OSR') == -1 : (b,m)= (False,m+'; Tag missing')
		event = Registry.get_primary_event()
		wplayer = LeaguePlayer.objects.filter(kgs_username__iexact = self.wplayer, event = event).first()
		bplayer = LeaguePlayer.objects.filter(kgs_username__iexact = self.bplayer, event = event).first()
		if wplayer != None and bplayer != None :
			if	wplayer.division != bplayer.division: (b,m) = (False,m+'; players not in same division')
			w_results = wplayer.get_results()
			if self.bplayer in w_results:
				if len(w_results[self.bplayer]) >= event.nb_matchs:
					(b,m) = (False,m+'; max number of games')
		else : (b,m) = (False,m+'; One of the players is not a league player')

		if not utils.check_byoyomi(self.byo):
			(b,m) = (False,m+'; byo-yomi')
		if int(self.time) < 1800: (b,m) = (False,m+'; main time')
		#no result shouldn't happen automaticly, but with admin upload, who knows
		if self.result == '?':(b,m) = (False,m+'; no result')
		if self.number_moves < 50 : (b,m) = (False,m+'; number moves')
		if Sgf.objects.filter(check_code=self.check_code).exists():(b,m) = (False,m+'; same sgf already in db')
		self.message = m
		self.league_valid = b
		return self






class User(AbstractUser):
	kgs_username = models.CharField(max_length=20)


	def join_event(self,event,division):
		if LeaguePlayer.objects.filter(user=self,event=event).exists():
			return False
		else :
			player = LeaguePlayer()
			player.event = event
			player.division = division
			player.kgs_username = self.kgs_username
			player.user = self
			player.save()
			return True

	def is_in_primary_event(self):
		event=Registry.get_primary_event()
		return LeaguePlayer.objects.filter(user=self,event=event).exists()

	def get_primary_event_player(self):
		event=Registry.get_primary_event()
		return LeaguePlayer.objects.filter(user=self,event=event).first()

	def user_is_league_admin(self):
		return self.groups.filter(name='league_admin').exists()

	def user_is_league_member(self):
		return self.groups.filter(name='league_member').exists()

	def nb_games(self):
		players = self.leagueplayer_set.all()
		n = 0
		for player in players:
			n += player.nb_games()
		return n

	def nb_players(self):
		return self.leagueplayer_set.all().count()

	def nb_win(self):
		players = self.leagueplayer_set.all()
		n = 0
		for player in players:
			n += player.nb_win
		return n

	def nb_loss(self):
		players = self.leagueplayer_set.all()
		n = 0
		for player in players:
			n += player.nb_loss
		return n



def is_league_admin(user):
	return user.groups.filter(name='league_admin').exists()
def is_league_member(user):
	return user.groups.filter(name='league_member').exists()



class Division(models.Model):
	league_event = models.ForeignKey('LeagueEvent')
	name = models.TextField(max_length=20)
	order = models.SmallIntegerField(default=0)

	class Meta:
		unique_together = ('league_event', 'order',)
		ordering = ['-league_event','order']

	def __str__(self):
		return self.name

	def get_players(self):
		return self.leagueplayer_set.all().order_by('-score')

	def number_players(self):
		return self.leagueplayer_set.count()

	def possible_games(self):
		n = self.number_players()
		return int(n*(n-1)*self.league_event.nb_matchs/2)



class LeaguePlayer(models.Model):
	user = models.ForeignKey('User')
	kgs_username = models.CharField(max_length=20,default='') #it's redundent with user, but let say a user change his kgs_username...
	event = models.ForeignKey('LeagueEvent')
	division = models.ForeignKey('Division')
	nb_win = models.SmallIntegerField(default=0)
	nb_loss = models.SmallIntegerField(default=0)
	score = models.DecimalField(default=0, max_digits=2, decimal_places=1)
	results = models.CharField(max_length=200,default='{}',blank=True)
	p_status = models.SmallIntegerField(default=0)
#Note that results is a dirty string formated as a dict.
# we will eval() to get it and str() to store.
# results is formated as:
#  {'opponent1':[{'id':game1.pk, 'r':1/0},{'id':game2.pk, 'r':1/0},...],'opponent2':[...]}
# r: 1 for win, 0 for loss
	def __str__(self):
		return self.kgs_username

	def get_results(self):
		return eval(self.results)

	def score_victory(self,opponent,game_id):
		#score a victory for self again opponent (a LeaguePlayer)
		# update score, nb_win and results
		self.nb_win +=  1
		self.score += self.event.ppwin
		dict_results = eval(self.results)
		opponent=opponent.kgs_username
		if opponent in dict_results :
			 dict_results[opponent].append({'id':game_id, 'r':1})
		else : dict_results[opponent]= [{'id':game_id, 'r':1}]
		str_results = str(dict_results)
		self.results = str_results
		self.save()

	def score_defeat(self,opponent,game_id):
		self.nb_loss +=  1
		self.score += self.event.pploss
		dict_results = eval(self.results)
		opponent=opponent.kgs_username
		if opponent in dict_results :
			dict_results[opponent].append({'id':game_id, 'r':0})
		else : dict_results[opponent]=[{'id':game_id, 'r':0}]
		str_results = str(dict_results)
		self.results = str_results
		self.save()

	def check_player(self):
		# check if a player have play new games:
		# get a list of games from kgs (only 1 request to kgs)
		# for each game we check if it's already in db (comparing urlto)
		# then we check if both players are in the same division(hence event)
		# if both we add them to db with p-status = 1 => to be scraped
		# if no do nothing
		# we can't get more info on the game yet cause we need the sgf datas for that.
		# So that would imply one additional kgs request per game in very short time.

		self.p_status =0
		self.save()
		kgs_username = self.user.kgs_username
		year = self.event.get_year()
		month = self.event.get_month()
		list_urlto_games=utils.ask_kgs(kgs_username,year,month)
		#list_urlto_games=[{url:'url',game_type:'game_type'},{...},...]
		for d in list_urlto_games:
			url=d['url']
			game_type=d['game_type']
			if  not Sgf.objects.filter(urlto = url).exists():
				#check if both players are in the league
				players = utils.extract_players_from_url(url)
				#no need to check the self to be in the league
				if players['white']==self.kgs_username:
					player = players['black']
				else:
					player = players['white']
				if LeaguePlayer.objects.filter(kgs_username__iexact=player,division=self.division).exists():
					sgf = Sgf()
					sgf.wplayer = players['white']
					sgf.bplayer = players['black']
					sgf.urlto = url
					sgf.p_status = 1
					sgf.game_type = game_type
					sgf.save()

	def nb_games(self):
		return(self.nb_win+self.nb_loss)

	def is_active(self):
		return self.nb_games() >= self.event.min_matchs


class Game(models.Model):
	sgf = models.OneToOneField('Sgf')
	event = models.ForeignKey('LeagueEvent',blank=True,null=True)
	black = models.ForeignKey('LeaguePlayer', related_name='black',blank=True,null=True)
	white = models.ForeignKey('LeaguePlayer',related_name='white',blank=True,null=True)
	winner = models.ForeignKey('LeaguePlayer',related_name='winner',blank=True,null=True)

	def __str__(self):
		return self.black.kgs_username + ' vs ' + self.white.kgs_username

	@staticmethod
	def create_game(sgf):
		# create a game related to the sgf
		# does NOT perform any check on the sgf. Just uses the league_valid flag
		# Please use check_validity before calling this
		# return true if successfully create a game, false otherwise

		#check if we already got a game with this sgf
		if Game.objects.filter(sgf=sgf).exists() or not(sgf.league_valid):
			return False
		else:
			event=Registry.get_primary_event()
			game = Game()
			game.event = event
			game.sgf = sgf
			game.save() #we need to save it to be able to add a OnetoOnefield
			whites = LeaguePlayer.objects.filter(kgs_username__iexact = sgf.wplayer).filter(event=event)
			if len(whites) == 1:
				 game.white = whites.first()
			else :
				game.delete()
				return False
			blacks = LeaguePlayer.objects.filter(kgs_username__iexact = sgf.bplayer).filter(event=event)
			if len(blacks) == 1:
				 game.black = blacks.first()
			else :
				game.delete()
				return False
			game.save()
			#add the winner field and score the results :
			if sgf.result.find('B+') == 0:
				game.winner = blacks.first()
				game.winner.score_victory(game.white,game.pk)
				game.white.score_defeat(game.black,game.pk)
			elif sgf.result.find('W+') == 0:
				game.winner = whites.first()
				game.winner.score_victory(game.black,game.pk)
				game.black.score_defeat(game.white,game.pk)

			else:
				game.delete()
				return False
			game.save()
			return True
