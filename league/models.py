from collections import defaultdict
import datetime
import json
from operator import attrgetter
import time

from django.contrib.auth.models import AbstractUser
from django.urls import reverse
from django.db import models
from django.db.models import Q
from django.utils import timezone
from machina.core import validators
from machina.models.fields import MarkupTextField
import pytz
import requests

from community.models import Community
from django_countries.fields import CountryField
from . import utils
from .ogs import get_user_rank

# pylint: disable=no-member

class LeagueEvent(models.Model):
    """A League.

    The Event name is unfortunate and should be removed mone day.
    """

    EVENT_TYPE_CHOICES = (
        ('ladder', 'ladder'),
        ('league', 'league'),
        ('meijin', 'meijin'),
        ('dan', 'dan'),
        ('ddk', 'ddk'),
        ('tournament', 'tournament'),
    )
    CLOCK_TYPE_CHOICES = (
        ('byoyomi', 'byoyomi'),
        ('fisher', 'fisher'),
    )
    #start and end of the league
    begin_time = models.DateTimeField(blank=True)
    end_time = models.DateTimeField(blank=True)
    # This should have been a charfield from the start.
    name = models.TextField(max_length=60)
    # max number of games 2 players are allowed to play together
    nb_matchs = models.SmallIntegerField(default=2)
    # points per win
    ppwin = models.DecimalField(default=1.5, max_digits=2, decimal_places=1)
    # points per loss
    pploss = models.DecimalField(default=0.5, max_digits=2, decimal_places=1)
    # minimum number of games to be consider as active
    min_matchs = models.SmallIntegerField(default=1)
    # In open leagues players can join and games get scraped
    is_open = models.BooleanField(default=False)
    # A non public league can only be seen by
    is_public = models.BooleanField(default=False)
    server = models.CharField(max_length=10, default='KGS')  # KGS, OGS
    event_type = models.CharField(  # ladder, tournament, league
        max_length=10,
        choices=EVENT_TYPE_CHOICES,
        default='ladder')
    tag = models.CharField(max_length=10, default='#OSR')
    komi = models.DecimalField(default=6.5, max_digits=2, decimal_places=1)

    clock_type = models.CharField(
        max_length=10,
        choices=CLOCK_TYPE_CHOICES,
        default='byoyomi')
    # main time in minutes
    main_time = models.PositiveSmallIntegerField(default=1800)
    # additional time in sec. Either byoyomi or per move if fisher
    additional_time = models.PositiveSmallIntegerField(default=30)

    board_size = models.PositiveSmallIntegerField(default=19)

    #if the league is a community league
    community = models.ForeignKey(Community, blank=True, null=True, on_delete=models.CASCADE)
    #small text to show on league pages
    description = MarkupTextField(
            blank=True, null=True,
            validators=[validators.NullableMaxLengthValidator(2000)]
    )
    prizes = MarkupTextField(
            blank=True, null=True,
            validators=[validators.NullableMaxLengthValidator(5000)]
    )

    class Meta:
        ordering = ['-begin_time']

    def __str__(self):
        return self.name

    def get_main_time_min(self):
        return self.main_time / 60

    def get_absolut_url(self):
        return reverse('league', kwargs={'pk': self.pk})

    def get_year(self):
        return self.begin_time.year

    def number_players(self):
        return self.leagueplayer_set.count()

    def number_games(self):
        return self.sgf_set.count()

    def number_divisions(self):
        return self.division_set.count()

    def possible_games(self):
        divisions = self.division_set.all()
        n = 0
        for division in divisions:
            n += division.possible_games()
        return n

    def percent_game_played(self):
        """Return the % of game played in regard of all possible games"""
        p = self.possible_games()
        if p == 0:
            n = 100
        else:
            n = round(float(self.number_games()) / float(self.possible_games()) * 100, 2)
        return n

    def get_divisions(self):
        """Return all divisions of this league"""
        return self.division_set.all()

    def get_players(self):
        """Return all leagueplayers of this league"""
        return self.leagueplayer_set.all()

    def number_actives_players(self):
        """Return the number of active players."""
        n = 0
        for player in self.get_players():
            if player.nb_games() >= self.min_matchs:
                n += 1
        return n

    def number_inactives_players(self):
        """Return the number of inactives players."""
        return self.number_players() - self.number_actives_players()

    def last_division_order(self):
        """Return the order of the last division of the league"""
        if self.division_set.exists():
            return self.division_set.last().order
        else:
            return -1

    def last_division(self):
        """get last division of a league"""
        if self.division_set.exists():
            return self.division_set.last()
        else:
            return False

    def get_other_events(self):
        """Returns all other leagues. Why?"""
        return LeagueEvent.objects.all().exclude(pk=self.pk)

    def is_close(self):
        """ why on earth?"""
        return self.is_close

    def nb_month(self):
        """Return a decimal representing the number of month in the event."""
        delta = self.end_time - self.begin_time
        return round(delta.total_seconds() / 2678400)

    def can_join(self, user):
        """Return a boolean saying if user can join this league.

        Note that user is not necessarily authenticated
        """
        if self.is_open and \
                user.is_authenticated and \
                user.is_league_member() and \
                not LeaguePlayer.objects.filter(user=user, event=self).exists():
            if self.community is None:
                return True
            else:
                return self.community.is_member(user)
        else:
            return False

    def can_quit(self, user):
        """return a boolean being true if a user can quit a league"""
        if not user.is_authenticated:
            return False
        player = LeaguePlayer.objects.filter(user=user, event=self).first()
        # no one should be able to quit a league if he have played games inside it.
        # we could think about a quite status for a player that would keep his games
        # but mark him quit.
        if player is None:
            return False
        black_sgfs = user.black_sgf.get_queryset().filter(events=self).exists()
        white_sgfs = user.white_sgf.get_queryset().filter(events=self).exists()
        if black_sgfs or white_sgfs:
            return False
        else:
            return True

    def remaining_sec(self):
        """return the number of milliseconds before the league ends."""
        delta = self.end_time - timezone.now()
        return int(delta.total_seconds() * 1000)

    @staticmethod
    def get_events(user):
        """Return all the leagues one user can see/join/play in."""
        if user.is_authenticated:
            communitys = user.get_communitys()
            events = LeagueEvent.objects.filter(
                Q(community__isnull=True) | Q(community__in=communitys) | Q(community__promote=True)
            )
            if not user.is_league_admin:
                events = events.filter(is_public=True)
        else:
            events = LeagueEvent.objects.filter(
                is_public=True,
                community__isnull=True
            )
        events = events.exclude(event_type='tournament').order_by('event_type')
        return events


class Registry(models.Model):
    """this class should only have one instance.

    Anyway, other than pk=0 won't be use
    """

    # We higlight one specific event
    primary_event = models.ForeignKey(LeagueEvent, on_delete=models.CASCADE)
    # number of byo yomi periods
    x_byo = models.PositiveSmallIntegerField(default=5)
    # last time we request kgs
    time_kgs = models.DateTimeField(default=datetime.datetime.now, blank=True)
    # time between 2 kgs get
    kgs_delay = models.SmallIntegerField(default=19)
    # actual meijin
    meijin = models.ForeignKey('User', null=True, blank=True, on_delete=models.CASCADE)

    @staticmethod
    def get_primary_event():
        r = Registry.objects.get(pk=1)
        return r.primary_event

    @staticmethod
    def get_time_kgs():
        r = Registry.objects.get(pk=1)
        return r.time_kgs

    @staticmethod
    def get_kgs_delay():
        r = Registry.objects.get(pk=1)
        return r.kgs_delay

    @staticmethod
    def set_time_kgs(time_kgs):
        r = Registry.objects.get(pk=1)
        r.time_kgs = time_kgs
        r.save()


class Sgf(models.Model):
    """A game record.

    When a sgf is added, we 1st add just the urlto
    then we add the rest with parse
    this is to prevent many kgs get request in short time
    """

    sgf_text = models.TextField(default='sgf')
    urlto = models.URLField(default='http://')
    wplayer = models.CharField(max_length=200, default='?')
    bplayer = models.CharField(max_length=200, default='?')
    place = models.CharField(max_length=200, default='?')
    result = models.CharField(max_length=200, default='?')
    league_valid = models.BooleanField(default=False)
    date = models.DateTimeField(default=datetime.datetime.now, blank=True, null=True)
    board_size = models.SmallIntegerField(default=19)
    handicap = models.SmallIntegerField(default=0)
    komi = models.DecimalField(default=6.5, max_digits=5, decimal_places=2)
    byo = models.CharField(max_length=20, default='sgf')
    time = models.PositiveIntegerField(default=19)
    game_type = models.CharField(max_length=20, default='Free')
    message = models.CharField(max_length=100, default='nothing', blank=True)
    number_moves = models.SmallIntegerField(default=100)
    p_status = models.SmallIntegerField(default=1)
    check_code = models.CharField(max_length=100, default='nothing', blank=True)
    events = models.ManyToManyField(LeagueEvent, blank=True)
    divisions = models.ManyToManyField('Division', blank=True)
    black = models.ForeignKey('User', blank=True, related_name='black_sgf', null=True, on_delete=models.CASCADE)
    white = models.ForeignKey('User', blank=True, related_name='white_sgf', null=True, on_delete=models.CASCADE)
    winner = models.ForeignKey('User', blank=True, related_name='winner_sgf', null=True, on_delete=models.CASCADE)
    ogs_id = models.PositiveIntegerField(blank=True, null=True)
    # black, white, winner and events fields will only be populated for valid sgfs
    # status of the sgf:0 already checked
    #           KGS status:
    #                   1 require checking, sgf added from kgs archive link
    #                   2 require checking with priority,sgf added/changed by admin
    #           OGS status:
    #                   3 require checking, sgf added from ogs api. We just got id

    def __str__(self):
        return str(self.pk) + ': ' + self.wplayer + ' vs ' + self.bplayer

    def get_players(self, event):
        """return the players of this sgf for this event."""

        [black_player, white_player] = [None, None]

        if self.place.startswith('OGS'):
            black_player = LeaguePlayer.objects.filter(
                event=event,
                ogs_username__iexact=self.bplayer
            ).first()

            white_player = LeaguePlayer.objects.filter(
                event=event,
                ogs_username__iexact=self.wplayer
            ).first()
        elif self.place.startswith('The KGS'):
            black_player = LeaguePlayer.objects.filter(
                event=event,
                kgs_username__iexact=self.bplayer
            ).first()

            white_player = LeaguePlayer.objects.filter(
                event=event,
                kgs_username__iexact=self.wplayer
            ).first()
        elif self.place.startswith('GOQUEST'):
            black_player = LeaguePlayer.objects.filter(
                event=event,
                go_quest_username__iexact=self.bplayer.split(" ")[0]
            ).first()

            white_player = LeaguePlayer.objects.filter(
                event=event,
                go_quest_username__iexact=self.wplayer.split(" ")[0]
            ).first()
        return [black_player, white_player]

    def update_related(self, events):
        """Update league_valid, events, divisions and users fields.
        return True if all went well and False if something went wrong
        """
        # First we empty all sgf related fields
        self.events.clear()
        self.divisions.clear()
        self.white = None
        self.black = None
        self.winner = None
        # We put the win info in a variable
        if self.result.find('B+') == 0:
            winner = 'black'
        elif self.result.find('W+') == 0:
            winner = 'white'
        else:  # here the game has no valid result.That shouldn't happen
            return False
        # if events is empty, we mark the sgf as invalid
        if len(events) == 0:
            self.league_valid = False
            self.save()
            return True
        else:
            for event in events:
                # Then we get the proper players
                [bplayer, wplayer] = self.get_players(event)
                if wplayer is None or bplayer is None:
                    return False
                # We add event and division to the sgf
                self.events.add(event)
                if not hasattr(event, 'stage') or event.stage == 1:
                    self.divisions.add(bplayer.division)

            # Now we set the fields on the sgf
            if winner == 'black':
                self.winner = bplayer.user
            else:
                self.winner = wplayer.user
            self.white = wplayer.user
            self.black = bplayer.user
            self.league_valid = True
            self.save()
            return True

    def get_messages(self):
        """Return a list of erros pasring message field."""
        return self.message.split(';')[1:]

    def parse(self):
        """Parse one sgf.

        check the p_status:
            0: return
            1: we only have urlto and need a server request
            2: uploaded/changed by admin and no kgs_request needed.
        Populate the rows(result, time, date...)
        Does NOT save sgf to db to allow previews of changes
        """
        if self.p_status == 0:
            return
        if self.p_status == 1:  # we only have the urlto and need a server request
            r = requests.get(self.urlto)
            if r.status_code == 403:
                # that's how OGS tells us a game is private.
                # game will then be deleted in scraper since results will still be ?
                # Starting to be a mess :(
                return self
            self.sgf_text = r.text
        prop = utils.parse_sgf_string(self.sgf_text)
        # prop['time'] = int(prop['time'])
        for k, v in prop.items():
            setattr(self, k, v)
        self.p_status = 0
        return self

    def is_duplicate(self):
        """Check if a sgf is already in the db comparing check_code.

        Return the sgf pk is duplicate and -1 if not.
        """
        sgfs = Sgf.objects.filter(check_code=self.check_code)
        if self.pk is None:  # self is not in the db already (admin uploading)
            if len(sgfs) > 0:
                return sgfs.first().pk
        else:  # If self is already in db, we need to check only with others sgfs
            sgfs = sgfs.exclude(pk=self.pk)
            if len(sgfs) > 0:
                return sgfs.first().pk
        return -1


    def check_players(self, event):
        m = ''
        b = True
        division = None
        [bplayer, wplayer] = self.get_players(event)
        if wplayer is not None and bplayer is not None:
            if wplayer.division != bplayer.division:
                (b, m) = (False, m + '; players not in same division')
            else:
                w_results = wplayer.get_results()
                if bplayer.user.pk in w_results:
                    if len(w_results[bplayer.user.pk]) >= event.nb_matchs:
                        (b, m) = (False, '; max number of games')
                    else:
                        division = bplayer.division
                else:
                    division = bplayer.division
        else:
            (b, m) = (False, '; One of the players is not a league player')
        return {'message': m, 'valid': b, 'division': division}

    def check_event_settings(self, event):
        """Check sgf settings for a given event.

        tag , timesetting,not a review
        We don't preform check on players. This will be done at check_players
        we don't touch the sgf but return a dict {'message': string , 'valid' : boolean, 'tag',boolean}
        Note that this method does not check if a sgf is already in db.
        """
        b = True
        m = ''
        if self.game_type == 'review':
            (b, m) = (False, m + ' review gametype')
        if event.tag in self.sgf_text or str.lower(event.tag) in self.sgf_text:
            tag = True
        else:
            tag = False
            (b, m) = (False, m + '; Tag missing')
        # check the time settings:
        if int(self.time) < event.main_time:
            (b, m) = (False, m + '; main time')

        if event.clock_type == 'byoyomi':
            byo = utils.get_byoyomi(self.byo)
            # if self.byo isn't byoyomi timesettings, we get [0,0] -> not valid
            if byo['n'] < 3 or byo['t'] < event.additional_time:
                (b, m) = (False, m + '; byo-yomi')
        # Beware: From the API, byo will be "30" but in the SGF we get "30 fischer"

        elif 'fischer' in self.byo:
            if int(self.byo.split(' ')[0]) < event.additional_time:
                (b, m) = (False, m + '; additional time')
        else:
            (b, m) = (False, m + '; Time settings')
        # no result shouldn't happen automaticly, but with admin upload, who knows
        if self.result == '?':
            (b, m) = (False, m + '; no result')
        if self.number_moves < 20:
            (b, m) = (False, m + '; number moves')
        # Here again, self.komi is a str !!!! Django allow saving str in decimal field in db?
        if float(self.komi) != event.komi:
            (b, m) = (False, m + '; komi')
        # self.board_size is added at parse. So it's a string. THat's a bug I fear.
        # dirty workaround is converting to int as above. We should convert when we parse.
        if int(self.board_size) != event.board_size:
            (b, m) = (False, m + '; board size')

        return {'message': m, 'valid': b, 'tag': tag, }

    def check_validity(self):
        """Check sgf validity for all open leaguesevents.

        Return a list of valid leagues is the sgf is valid and [] if not
        Update the sgf but do NOT save it to db. This way allow some preview.
        I think the way we deal with message could be better:
        maybe a dict with {'event1':'message', 'event2'...}
        """
        # First we check if we have same sgf in db comparing check_code
        duplicate = self.is_duplicate()
        if duplicate > 0:
            self.league_valid = False
            self.message = 'same sgf already in db : ' + str(duplicate)
            return []

        events = LeagueEvent.objects.filter(is_open=True).exclude(event_type='tournament')  # get all open events
        message = ''
        # if no open events, the sgf can't be valid
        if len(events) == 0:
            return []
        valid_events = []
        for event in events:
            settings = self.check_event_settings(event)
            players = self.check_players(event)
            check = {
                'message': players['message'] + settings['message'],
                'valid': players['valid'] and settings['valid'],
                'tag': settings['tag'],
                'players': players['valid']
            }
            # if the players are in this event, we keep this events message
            if check['players']:
                message = check['message']
                if check['valid']:
                    valid_events.append(event)

        if len(valid_events) == 0:
            # here sgf is valid for no event.
            # if the sgf was tagged for an event, we display this event message.
            # Otherwise, just the last one.
            self.league_valid = False
            if len(message) > 0:
                self.message = message
            else:
                self.message = check['message']
            return []
        else:  # the sgf is valid for at lease one event.
            self.league_valid = True
            self.message = ''
            return valid_events


class User(AbstractUser):
    """User used for auth in all project."""

    kgs_username = models.CharField(max_length=20, null=True, blank=True)

    def __init__(self, *args, **kwargs):
        AbstractUser.__init__(self, *args, **kwargs)
        self.n_loss = None
        self.n_win = None
        self.n_games = None


    def join_event(self, event, division):
        if not event.can_join(self):
            return False
        else:
            player = LeaguePlayer()
            player.event = event
            player.division = division
            player.kgs_username = self.profile.kgs_username
            player.ogs_username = self.profile.ogs_username
            player.user = self
            player.save()
            return True

    def is_online(self):
        """return a boolean saying if a user is online in either KGS, OGS or discord"""
        if self.discord_user.first() is not None:
            discord_online = self.discord_user.first().status != 'offline'
        else:
            discord_online = False
        return self.is_online_kgs() or self.is_online_ogs() or discord_online

    def is_online_kgs(self):
        """return a boolean saying if a user is online on KGS."""
        if self.profile.last_kgs_online is None:
            return False
        now = timezone.now()
        delta = now - self.profile.last_kgs_online
        return delta.total_seconds() < 500

    def is_online_ogs(self):
        """return a boolean saying if a user is online on OGS."""
        if self.profile.last_ogs_online is None:
            return False
        now = timezone.now()
        delta = now - self.profile.last_ogs_online
        return delta.total_seconds() < 500

    def is_in_primary_event(self):
        event = Registry.get_primary_event()
        return LeaguePlayer.objects.filter(user=self, event=event).exists()

    def is_in_event(self, event):
        return LeaguePlayer.objects.filter(user=self, event=event).exists()

    def get_primary_event_player(self):
        event = Registry.get_primary_event()
        return LeaguePlayer.objects.filter(user=self, event=event).first()

    def is_league_admin(self, event=None):
        """
        If event is none, we test if user is in league_admin group.

        Else we test if the event is a community league and if so,
         we test if user is in this community admin group
        """
        if self.groups.filter(name='league_admin').exists():
            return True
        if event is not None:
            if event.community is not None:
                return event.community.is_admin(self)
            if event.event_type == 'tournament':
                return self.groups.filter(name='tournament_master').exists()
        return False

    def is_league_member(self):
        return self.groups.filter(name='league_member').exists()

    def is_osr_admin(self):
        return self.groups.filter(name='OSR_admin').exists()


    def nb_games(self):
        players = self.leagueplayer_set.all()
        n = 0
        for player in players:
            n += player.nb_games()
        return n

    def nb_players(self):
        return self.leagueplayer_set.all().count()

    def nb_win(self):
        #return self.winner_sgf.count()
        players = self.leagueplayer_set.all()
        n = 0
        for player in players:
            n += player.nb_win()
        return n

    def nb_loss(self):
        players = self.leagueplayer_set.all()
        n = 0
        for player in players:
            n += player.nb_loss()
        return n

    def get_stats(self):
        """get number of games, win, loss and add them as attributes to self."""
        self.n_games = self.black_sgf.count() + self.white_sgf.count()
        self.n_win = self.winner_sgf.count()
        self.n_loss = self.n_games - self.n_win
        return self

    def get_primary_email(self):
        return self.emailaddress_set.filter(primary=True).first()

    def get_open_divisions(self):
        """Return all open division a user is in."""
        players = self.leagueplayer_set.all()
        return Division.objects.filter(leagueplayer__in=players, league_event__is_open=True)

    def get_opponents(self, divs_list=None, server_list=None):
        """return a list of all user self can play with.

        return empty list if the user is not in any active league.
        The optional param divs_list allow to filter only opponents of some divisions.
        Maybe at some point we should have the divisions in which on can play with
        as well as the number of games remaining.
        """
        # First we get all self players in open divisions
        players = self.leagueplayer_set.filter(division__league_event__is_open=True)
        if divs_list is not None:
            players = players.filter(division__in=divs_list)
        if len(players) == 0:
            return []
        # For each player, we get related opponents
        opponents = []
        for player in players:
            division = player.division
            player_opponents = LeaguePlayer.objects.filter(
                division=division).exclude(pk=player.pk)
            if server_list is not None:
                if 'OGS' in server_list:
                    player_opponents = player_opponents.exclude(
                        user__profile__ogs_id=0
                    )
                if 'KGS' in server_list:
                    player_opponents = player_opponents\
                        .exclude(user__profile__kgs_username__isnull=True)\
                        .exclude(user__profile__kgs_username=u'')
            for opponent in player_opponents:
                n_black = player.user.black_sgf.get_queryset().filter(
                    divisions=division,
                    white=opponent.user).count()
                n_white = player.user.white_sgf.get_queryset().filter(
                    divisions=division,
                    black=opponent.user).count()
                if n_white + n_black < division.league_event.nb_matchs:
                    if opponent.user not in opponents:
                        opponents.append(opponent.user)
        return opponents


    @staticmethod
    def kgs_online_users():
        """Return a list of all user in open leagues online on KGS."""
        time_online = timezone.now() - datetime.timedelta(minutes=6)
        # First we get all self players in open divisions
        players = LeaguePlayer.objects\
            .filter(division__league_event__is_open=True)\
            .filter(
                Q(user__profile__last_kgs_online__gt=time_online) |
                Q(user__profile__last_ogs_online__gt=time_online) |
                Q(user__discord_user__status='online')
            ).values_list('user', flat=True)
        return players

    def check_kgs(self, opponents):
        """check if a user have played some new games in KGS

                get a list of games from kgs (only 1 request to kgs)
                for each game we check if it's already in db (comparing urlto)
                then, for each user.players in open events,
                we check if user.player and his opponent are in the same division
                    - if yes: we add them to db with p-status = 1 => to be scraped
                    - if no: we do nothing
                We can't get more info on the game yet cause we need the sgf datas for that.
                So that would imply one additional kgs request per game in very short time.
                """

        now = datetime.datetime.today()
        # Get the time-range to check
        # months is a set with current month
        months = [{'month': now.month, 'year': now.year}]
        if now.day == 1:
            # if we are the 1st of the month, we check both previous month an current
            prev = now.replace(day=1) - datetime.timedelta(days=1)
            months.append({'month': prev.month, 'year': prev.year})
        kgs_username = self.profile.kgs_username
        opponents = [opponent.profile.kgs_username.lower() for opponent in opponents]
        list_urlto_games = utils.ask_kgs(
            kgs_username,
            months[0]['year'],
            months[0]['month']
        )
        if len(months) > 1:
            time.sleep(3)
            list_urlto_games += utils.ask_kgs(
                kgs_username,
                months[1]['year'],
                months[1]['month']
            )
        # list_urlto_games=[{url:'url',game_type:'game_type'},{...},...]
        for d in list_urlto_games:
            url = d['url']
            game_type = d['game_type']
            # don't record the simuls
            if game_type == 'Simul':
                continue
            # First we check if we already have a sgf with same urlto in db
            if not Sgf.objects.filter(urlto=url).exists():
                # check if both players are in the league
                players = utils.extract_players_from_url(url)
                # no need to check the self to be in the league
                if players['white'].lower() == self.profile.kgs_username.lower():
                    opponent = players['black'].lower()
                else:
                    opponent = players['white'].lower()
                # Finally, we check if player and oponents
                # are in an open event's same division
                if opponent in opponents:
                    sgf = Sgf()
                    sgf.wplayer = players['white']
                    sgf.bplayer = players['black']
                    sgf.urlto = url
                    sgf.p_status = 1
                    sgf.game_type = game_type
                    sgf.save()

    def check_ogs(self, opponents):
        """Checking user for OGS games.
        """
        # Get the time-range to check
        # we just create a date with 1st of the month at 00:00
        now = datetime.datetime.today()
        if now.day == 1:
            # if we are the 1st of the month, we go to previous month
            now = now.replace(day=1) - datetime.timedelta(days=1)
        # Set day, time to 0
        time_limit = now.replace(day=1, hour=0, minute=0)
        ogs_id = self.profile.ogs_id
        url = 'https://online-go.com/api/v1/players/' +\
            str(ogs_id) +\
            '/games/?ordering=-ended&ended__gt=' +\
            datetime.datetime.strftime(time_limit, '%Y-%m-%d %H:%M')
        opponents = [u.profile.ogs_id for u in opponents if u.profile.ogs_id > 0]

        # we deal with pagination with this while loop
        while url is not None:
            request = requests.get(url).json()
            url = request['next']
            for game in request['results']:
                # first we check if end date og game is too old
                # 2013-08-31T12:47:34.887Z
                if game['ended']:
                    game_ended = datetime.datetime.strptime(
                        game['ended'],
                        '%Y-%m-%dT%H:%M:%S.%fZ')
                else:
                    continue
                if game_ended < time_limit:
                    break
                # then we check if we have the same  id in db.
                # Since it's ordered by time, no need to keep going. but we do?
                if Sgf.objects.filter(ogs_id=game['id']).exists():
                    continue

                # we get opponent ogs id
                if game['white'] == ogs_id:
                    opponent_ogs_id = game['black']
                else:
                    opponent_ogs_id = game['white']
                # Check if opponent is a opponent
                if opponent_ogs_id not in opponents:
                    continue

                # we need to get timesetting datas here because they are not
                # in OGS sgfs
                time_settings = json.loads(game["time_control_parameters"])
                # Some SGF does not have "system" in time_settings. Why? when?
                # we had this check in the commit 3cea232.
                if 'system' not in time_settings:
                    continue
                sgf = Sgf()
                if time_settings['system'] == "byoyomi":
                    sgf.time = time_settings['main_time']
                    # Sadly byo is recorded as a string 3x30 byo-yomi in db
                    sgf.byo = str(time_settings['periods']) + 'x' + \
                        str(time_settings['period_time']) + ' byo-yomi'

                elif time_settings['system'] == "fischer":
                    sgf.time = time_settings['initial_time']
                    sgf.byo = str(time_settings['time_increment'])
                else:
                    continue

                sgf.wplayer = game['players']['white']['username']
                sgf.bplayer = game['players']['black']['username']
                sgf.urlto = 'https://online-go.com/api/v1/games/' +\
                    str(game['id']) + '/sgf/'
                sgf.ogs_id = game['id']
                sgf.p_status = 1
                sgf.save()
            # this else will be executed only if no break appeared in the inner loop
            else:
                time.sleep(2)
                continue
            # breaking the inner loop will break it all
            break

    def check_user(self):
        """Check a user to see if he have play new games.

        We test KGS and OGS depending if the user have some usernames in his profile.
         """
        # get the opponents one can play with
        opponents = self.get_opponents()
        # Ask servers
        if self.profile.kgs_username is not None:
            self.check_kgs(opponents)
        if self.profile.ogs_id > 0:
            self.check_ogs(opponents)
            self.profile.ogs_rank = get_user_rank(self.profile.ogs_id)  # set new rank
        # Mark the user checked
        self.profile.p_status = 0
        self.profile.save()

    def get_timezone(self):
        """Return the timezone of a user"""
        if (self.is_authenticated and
                hasattr(self, 'profile') and
                self.profile.timezone is not None):
            tz = pytz.timezone(self.profile.timezone)
        else:
            tz = pytz.utc
        return tz

    def set_meijin(self):
        """Set a user as OSR meijin"""
        r = Registry.objects.get(pk=1)
        r.meijin = self
        r.save()
        return True

    def get_communitys(self):
        """Get all communities a user is in"""
        communitys = self.groups.filter(name__endswith='community_member')
        communitys = list(Community.objects.filter(user_group__in=communitys))
        return communitys


class Profile(models.Model):
    """A user profile. Store settings and infos about a user."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    kgs_username = models.CharField(max_length=10, blank=True)
    ogs_username = models.CharField(max_length=40, blank=True)
    go_quest_username = models.CharField(max_length=40, blank=True)
    kgs_rank = models.CharField(max_length=40, blank=True)
    ogs_rank = models.CharField(max_length=40, blank=True)
    # ogs_id is set in ogs.get_user_id
    ogs_id = models.PositiveIntegerField(default=0, blank=True, null=True)
    # User can write what he wants in bio
    bio = MarkupTextField(
            blank=True, null=True,
            validators=[validators.NullableMaxLengthValidator(2000)]
    )
    # p_status help manage the scraplist
    p_status = models.PositiveSmallIntegerField(default=0)
    # kgs_online shoudl be updated every 5 mins in scraper
    last_kgs_online = models.DateTimeField(blank=True, null=True)
    last_ogs_online = models.DateTimeField(blank=True, null=True)

    # Calendar settings
    timezone = models.CharField(
        max_length=100,
        choices=[(t, t) for t in pytz.common_timezones],
        blank=True, null=True
    )
    start_cal = models.PositiveSmallIntegerField(default=0)
    end_cal = models.PositiveSmallIntegerField(default=24)
    picture_url = models.URLField(blank=True, null=True)
    country = CountryField(blank=True, null=True, blank_label='(select country)')

    def __str__(self):
        return self.user.username


class Division(models.Model):
    """A group of players in a league"""
    league_event = models.ForeignKey('LeagueEvent', on_delete=models.CASCADE,)
    name = models.TextField(max_length=20)
    order = models.SmallIntegerField(default=0)
    winner = models.ForeignKey(
        'User',
        null=True,
        blank=True,
        related_name="won_division",
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = ('league_event', 'order',)
        ordering = ['-league_event', 'order']

    def __str__(self):
        return self.name + self.league_event.name

    def number_games(self):
        return self.sgf_set.distinct().count()

    def get_players(self):
        return self.leagueplayer_set.all()

    def number_players(self):
        return self.leagueplayer_set.count()

    def possible_games(self):
        n = self.number_players()
        return int(n * (n - 1) * self.league_event.nb_matchs / 2)

    def is_first(self):
        """return a boolean being True if the division is the first of the league."""
        return not Division.objects.filter(
            league_event=self.league_event,
            order__lt=self.order
        ).exists()

    def is_last(self):
        """return a boolean being True if the division is the last of the league."""
        return not Division.objects.filter(
            league_event=self.league_event,
            order__gt=self.order
        ).exists()

    def get_results(self):
        """New proper way to get results.

        return a list of all leagueplayers of the division with extra fields:
            - rank : integer
            - score : decimal
            - nb_win : integer
            - nb_loss : integer
            - nb_games : integer
            - results : a dict as such
            - is_active : true/false
            {opponent1 : [{'id':game1.pk, 'r':1/0},{'id':game2.pk, 'r':1/0},...],opponent2:}
        """
        sgfs = self.sgf_set.defer('sgf_text').select_related('winner', 'white', 'black').all()
        players = LeaguePlayer.objects.filter(division=self).prefetch_related('user__profile')
        # First create a list of players with extra fields
        results = []
        for player in players:
            player.n_win = 0
            player.n_loss = 0
            player.n_games = 0
            player.score = 0
            player.results = {}
            player.sos = 0
            player.sodos = 0
            results.append(player)
        for sgf in sgfs:
            if sgf.winner == sgf.white:
                loser = next(player for player in results if player.user == sgf.black)
                winner = next(player for player in results if player.user == sgf.white)
            else:
                loser = next(player for player in results if player.user == sgf.white)
                winner = next(player for player in results if player.user == sgf.black)
            winner.n_win += 1
            winner.n_games += 1
            winner.score += self.league_event.ppwin
            loser.n_loss += 1
            loser.n_games += 1
            loser.score += self.league_event.pploss
            if loser.pk in winner.results:
                winner.results[loser.pk].append({'id': sgf.pk, 'r': 1, 'p': sgf.result})
            else:
                winner.results[loser.pk] = [{'id': sgf.pk, 'r': 1, 'p': sgf.result}]
            if winner.pk in loser.results:
                loser.results[winner.pk].append({'id': sgf.pk, 'r': 0, 'p': sgf.result})
            else:
                loser.results[winner.pk] = [{'id': sgf.pk, 'r': 0, 'p': sgf.result}]

        # now let's set the active flag
        min_matchs = self.league_event.min_matchs
        for player in players:
            player.is_active = player.n_games >= min_matchs

        real_opponent = {}
        # calulcate the sos for each player
        for player in players:
            for opponent, info in player.results.items():
                for opponent_player in players:
                    if opponent is opponent_player.pk:
                        real_opponent = opponent_player
                for list_item in info:
                    if list_item.get('r') is 1:
                        player.sodos += real_opponent.n_win
                    player.sos += real_opponent.n_win

        results = sorted(
            results,
            key=attrgetter('score', 'n_games', 'sos', 'sodos'),
            reverse=True
        )
        return results


class LeaguePlayer(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    kgs_username = models.CharField(max_length=20, default='', null=True, blank=True)
    ogs_username = models.CharField(max_length=40, null=True, blank=True)
    go_quest_username = models.CharField(max_length=40, null=True, blank=True)

    #kgs_rank = models.CharField(max_length=20, default='')
    event = models.ForeignKey('LeagueEvent', on_delete=models.CASCADE)
    division = models.ForeignKey('Division', null=True, blank=True, on_delete=models.CASCADE)
    # p_status is deprecated, we now store that in player profile
    p_status = models.SmallIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'division',)

    def __str__(self):
        return str(self.pk) + ": " + self.user.username + ", " + self.event.name

    def get_results(self):
        """Return a player results.

        results are formated as:
        {'opponent1':[{'id':game1.pk, 'r':1/0},{'id':game2.pk, 'r':1/0},...],'opponent2':[...]}
        r: 1 for win, 0 for loss
        """
        black_sgfs = self.user.black_sgf.get_queryset().filter(divisions=self.division)
        white_sgfs = self.user.white_sgf.get_queryset().filter(divisions=self.division)
        resultsDict = defaultdict(list)

        for sgf in black_sgfs:
            opponent = sgf.white
            won = sgf.winner == self.user
            record = {
                'id': sgf.pk,
                'r': 1 if won else 0
            }
            resultsDict[opponent.pk].append(record)

        for sgf in white_sgfs:
            opponent = sgf.black
            won = sgf.winner == self.user
            record = {
                'id': sgf.pk,
                'r': 1 if won else 0
            }
            resultsDict[opponent.pk].append(record)
        return resultsDict

    def nb_win(self):
        user = self.user
        event = self.event
        return event.sgf_set.filter(
            Q(black=user) | Q(white=user)).filter(winner=user).count()

    def nb_loss(self):
        user = self.user
        event = self.event
        return event.sgf_set.filter(
            Q(black=user) | Q(white=user)).exclude(winner=user).count()

    def nb_games(self):
        user = self.user
        event = self.event
        return event.sgf_set.filter(Q(black=user) | Q(white=user)).count()

    def score_win(self):
        self.score += self.event.ppwin
        self.save()

    def score_loss(self):
        self.score += self.event.pploss
        self.save()

    def unscore_win(self):
        self.score -= self.event.ppwin
        self.save()

    def unscore_loss(self):
        self.score -= self.event.pploss
        self.save()

    def get_opponents(self):
        """return a list of players"""
        players = LeaguePlayer.objects.filter(division=self.division).exclude(pk=self.pk)
        opponents = []
        for player in players:
            n_black = self.user.black_sgf.get_queryset().filter(
                divisions=self.division,
                white=player.user).count()
            n_white = self.user.white_sgf.get_queryset().filter(
                divisions=self.division,
                black=player.user).count()
            if n_white + n_black < self.event.nb_matchs:
                opponents.append(player)
        return opponents
