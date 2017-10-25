from django.db import models
import datetime
import time
from . import utils
import requests
from django.contrib.auth.models import AbstractUser
from collections import defaultdict
from django.db.models import Q
import pytz
from operator import attrgetter
from django.core.urlresolvers import reverse
from django.utils import timezone
from community.models import Community
from machina.models.fields import MarkupTextField
from machina.core import validators
import json


# Create your models here.

class LeagueEvent(models.Model):
    """A League.

    The Event name is unfortunate and should be removed mone day.
    """

    EVENT_TYPE_CHOICES = (
        ('ladder', 'ladder'),
        ('league', 'league'),
        ('tournament', 'tournament'),
        ('meijin', 'meijin'),
        ('ddk', 'ddk'),

    )
    begin_time = models.DateTimeField(blank=True)
    end_time = models.DateTimeField(blank=True)
    # This should have been a charfield from the start.
    name = models.TextField(max_length=20)
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
    # main time in minutes
    main_time = models.PositiveSmallIntegerField(default=1800)
    # byo yomi time in sec
    byo_time = models.PositiveSmallIntegerField(default=30)
    community = models.ForeignKey(Community, blank=True, null=True)
    description = MarkupTextField(
            blank=True, null=True,
            validators=[validators.NullableMaxLengthValidator(2000)]
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
        p = self.possible_games()
        if p == 0:
            n = 100
        else:
            n = round(float(self.number_games()) / float(self.possible_games()) * 100, 2)
        return n

    def get_divisions(self):
        return self.division_set.all()

    def get_players(self):
        return self.leagueplayer_set.all()

    def number_actives_players(self):
        n = 0
        for player in self.get_players():
            if player.nb_games() >= self.min_matchs:
                n += 1
        return n

    def number_inactives_players(self):
        return (self.number_players() - self.number_actives_players())

    def last_division_order(self):
        if self.division_set.exists():
            return self.division_set.last().order
        else:
            return -1

    def last_division(self):
        if self.division_set.exists():
            return self.division_set.last()
        else:
            return False

    def get_other_events(self):
        return LeagueEvent.objects.all().exclude(pk=self.pk)

    def is_close(self):
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
        return events


class Registry(models.Model):
    """this class should only have one instance.

    Anyway, other than pk=0 won't be use
    """

    # We higlight one specific event
    primary_event = models.ForeignKey(LeagueEvent)
    # number of byo yomi periods
    x_byo = models.PositiveSmallIntegerField(default=5)
    # last time we request kgs
    time_kgs = models.DateTimeField(default=datetime.datetime.now, blank=True)
    # time between 2 kgs get
    kgs_delay = models.SmallIntegerField(default=19)
    # actual meijin
    meijin = models.ForeignKey('User', null=True, blank=True)

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
    def set_time_kgs(time):
        r = Registry.objects.get(pk=1)
        r.time_kgs = time
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
    date = models.DateTimeField(default=datetime.datetime.now, blank=True)
    board_size = models.SmallIntegerField(default=19)
    handicap = models.SmallIntegerField(default=0)
    komi = models.DecimalField(default=6.5, max_digits=5, decimal_places=2)
    byo = models.CharField(max_length=20, default='sgf')
    time = models.SmallIntegerField(default=19)
    game_type = models.CharField(max_length=20, default='Free')
    message = models.CharField(max_length=100, default='nothing', blank=True)
    number_moves = models.SmallIntegerField(default=100)
    p_status = models.SmallIntegerField(default=1)
    check_code = models.CharField(max_length=100, default='nothing', blank=True)
    events = models.ManyToManyField(LeagueEvent, blank=True)
    divisions = models.ManyToManyField('Division', blank=True)
    black = models.ForeignKey('User', blank=True, related_name='black_sgf', null=True)
    white = models.ForeignKey('User', blank=True, related_name='white_sgf', null=True)
    winner = models.ForeignKey('User', blank=True, related_name='winner_sgf', null=True)
    ogs_id = models.PositiveIntegerField(blank=True, null=True)
    # black, white, winner and events fields will only be populated for valid sgfs
    # status of the sgf:0 already checked
    #           KGS status:
    # 					1 require checking, sgf added from kgs archive link
    # 					2 require checking with priority,sgf added/changed by admin
    #           OGS status:
    #                   3 require checking, sgf added from ogs api. We just got id

    def __str__(self):
        return str(self.pk) + ': ' + self.wplayer + ' vs ' + self.bplayer

    def get_players(self, event):
        """return the players of this sgf for this event."""
        if self.ogs_id:
            black_player = LeaguePlayer.objects.filter(
                event=event,
                ogs_username__iexact=self.bplayer
            )

            white_player = LeaguePlayer.objects.filter(
                event=event,
                ogs_username__iexact=self.wplayer
            )
        else:
            black_player = LeaguePlayer.objects.filter(
                event=event,
                kgs_username__iexact=self.bplayer
            )

            white_player = LeaguePlayer.objects.filter(
                event=event,
                kgs_username__iexact=self.wplayer
            )
        if len(black_player) == 1:  # That shouldn't happen, but who knows
            black_player = black_player.first()
        else:
            return False
        if len(white_player) == 1:
            white_player = white_player.first()
        else:
            return False
        return {'black': black_player, 'white': white_player}

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
                players = self.get_players(event)
                if players is False:
                    return False
                # We add event and division to the sgf
                self.events.add(event)
                self.divisions.add(players['black'].division)
            # Now we set the fields on the sgf
            if winner == 'black':
                self.winner = players['black'].user
            else:
                self.winner = players['white'].user
            self.white = players['white'].user
            self.black = players['black'].user
            self.league_valid = True
            self.save()
            return True

    def has_game(self):
        """Deprecated. We should use league_valid from now on."""
        return Game.objects.filter(sgf=self).exists()

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
            self.sgf_text = r.text
        prop = utils.parse_sgf_string(self.sgf_text)
        # prop['time'] = int(prop['time'])
        for k, v in prop.items():
            setattr(self, k, v)
        self.p_status = 0
        return self

    def check_validity_event(self, event):
        """Check sgf validity for a given event.

        oponents in same Division, tag , timesetting,not a review
        We will reperform check on players division because a user could have upload a sgf by hand
        hence such a sgf wouldn't have been check during check_player
        we don't touch the sgf but return a dict {'message': string , 'valid' : boolean, 'tag',boolean}
        This is meant to be called by check_validity(self) only.
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
        if self.ogs_id is not None:
            wplayer = LeaguePlayer.objects.filter(
                ogs_username__iexact=self.wplayer,
                event=event
            ).first()
            bplayer = LeaguePlayer.objects.filter(
                ogs_username__iexact=self.bplayer,
                event=event
            ).first()

        else:
            wplayer = LeaguePlayer.objects.filter(
                kgs_username__iexact=self.wplayer,
                event=event
            ).first()
            bplayer = LeaguePlayer.objects.filter(
                kgs_username__iexact=self.bplayer,
                event=event
            ).first()
        if wplayer is not None and bplayer is not None:
            if wplayer.division != bplayer.division:
                (b, m) = (False, m + '; players not in same division')
            else:
                w_results = wplayer.get_results()
                if self.bplayer in w_results:
                    if len(w_results[self.bplayer]) >= event.nb_matchs:
                        (b, m) = (False, m + '; max number of games')
        else:
            (b, m) = (False, m + '; One of the players is not a league player')

        if not utils.check_byoyomi(self.byo):
            (b, m) = (False, m + '; byo-yomi')
        if int(self.time) < event.main_time:
            (b, m) = (False, m + '; main time')
        # no result shouldn't happen automaticly, but with admin upload, who knows
        if self.result == '?':
            (b, m) = (False, m + '; no result')
        if self.number_moves < 20:
            (b, m) = (False, m + '; number moves')
        if not self.komi.startswith('6.5'):
            (b, m) = (False, m + '; komi')
        return {'message': m, 'valid': b, 'tag': tag, }

    def check_validity(self):
        """Check sgf validity for all open events.

        Return a list of valid leagues is the sgf is valid and [] if not
        Update the sgf but do NOT save it to db. This way allow some preview.
        I think the way we deal with message could be better:
        maybe a dict with {'event1':'message', 'event2'...}
        """
        # First we check if we have same sgf in db comparing check_code
        sgfs = Sgf.objects.filter(check_code=self.check_code)
        if self.pk is None:  # self is not in the db already (admin uploading)
            if len(sgfs) > 0:
                self.league_valid = False
                self.message = 'same sgf already in db : ' + str(sgfs.first().pk)
                return []
        else:  # If self is already in db, we need to check only with others sgfs
            sgfs = sgfs.exclude(pk=self.pk)
            if len(sgfs) > 0:
                self.league_valid = False
                self.message = ';same sgf already in db : ' + str(sgfs.first().pk)
                # if sgf already in db, no need to perform further.
                return []

        events = LeagueEvent.objects.filter(is_open=True)  # get all open events
        message = ''
        # if no open events, the sgf can't be valid
        if len(events) == 0:
            return []
        valid_events = []
        for event in events:
            check = self.check_validity_event(event)
            # if the game is taged for this event, we keep this events message
            if check['tag']:
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

    def is_online_kgs(self):
        """return a boolean saying if a user is online on KGS."""
        if self.profile.last_kgs_online is None:
            return False
        now = timezone.now()
        delta = now - self.profile.last_kgs_online
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
        if event is None or event.community is None:
            return self.groups.filter(name='league_admin').exists()
        else:
            return event.community.is_admin(self)

    def is_league_member(self):
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
            n += player.nb_win()
        return n

    def nb_loss(self):
        players = self.leagueplayer_set.all()
        n = 0
        for player in players:
            n += player.nb_loss()
        return n

    def get_primary_email(self):
        return self.emailaddress_set.filter(primary=True).first()

    def get_open_divisions(self):
        """Return all open division a user is in."""
        players = self.leagueplayer_set.all()
        return Division.objects.filter(leagueplayer__in=players, league_event__is_open=True)

    def get_opponents(self, divs_list=None):
        """return a list of all user self can play with.
        return False if the user is not in any active league.
        The optional param divs_list allow to filter only opponents of some divisions.
        Maybe at some point we should have the divisions in which on can play with
        as well as the number of games remaining.
        """
        # First we get all self players in open divisions
        players = self.leagueplayer_set.filter(division__league_event__is_open=True)
        if divs_list is not None:
            players = players.filter(division__in=divs_list)
        if len(players) == 0:
            return False
        # For each player, we get related opponents
        opponents = []
        for player in players:
            division = player.division
            player_opponents = LeaguePlayer.objects.filter(
                division=division).exclude(pk=player.pk)
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
        time_online = timezone.now() - datetime.timedelta(minutes=6)
        # First we get all self players in open divisions
        players = LeaguePlayer.objects.filter(
            division__league_event__is_open=True,
            user__profile__last_kgs_online__gt=time_online
        ).values_list('user',flat=True)
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

    def check_ogs(user, opponents):
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
        ogs_id = user.profile.ogs_id
        url = 'https://online-go.com/api/v1/players/' + str(ogs_id) + '/games/?ordering=-ended'
        opponents = [u.profile.ogs_id for u in opponents if u.profile.ogs_id > 0]
        # we deal with pagination with this while loop
        while url is not None:
            request = requests.get(url).json()
            url = request['next']
            for game in request['results']:
                # first we check if we have the same  id in db.
                # Since it's ordered by time, no need to keep going.
                if Sgf.objects.filter(ogs_id=game['id']).exists():
                    continue
                # Then we check if end date og game is too old
                # 2013-08-31T12:47:34.887Z
                if game['ended']:
                    game_ended = datetime.datetime.strptime(
                        game['ended'],
                        '%Y-%m-%dT%H:%M:%S.%fZ')
                else:
                    continue
                if game_ended < time_limit:
                    break
                # we get opponent ogs id
                if game['white'] == ogs_id:
                    opponent_ogs_id = game['black']
                else:
                    opponent_ogs_id = game['white']
                # Check if opponent is a opponent
                if opponent_ogs_id in opponents:
                    # we need to get timesetting datas here because they are not
                    # in OGS sgfs
                    time_settings = json.loads(game["time_control_parameters"])
                    if time_settings['system'] == "byoyomi":
                        sgf = Sgf()
                        sgf.time = time_settings['main_time']
                        # Sadly byo is recorded as a string 3x30 byo-yomi in db
                        sgf.byo = str(time_settings['periods']) + 'x' + \
                            str(time_settings['period_time']) + ' byo-yomi'
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
        if self.profile.ogs_id >0:
            self.check_ogs(opponents)
        # Mark the user checked
        self.profile.p_status = 0
        self.profile.save()



    def get_timezone(self):
        if (self.is_authenticated() and
                hasattr(self, 'profile') and
                self.profile.timezone is not None):
            tz = pytz.timezone(self.profile.timezone)
        else:
            tz = pytz.utc
        return tz

    def set_meijin(self):
        r = Registry.objects.get(pk=1)
        r.meijin = self
        r.save()
        return True

    def get_communitys(self):
        communitys = self.groups.filter(name__endswith='community_member')
        communitys = list(Community.objects.filter(user_group__in=communitys))
        return communitys



class Profile(models.Model):
    user = models.OneToOneField(User)
    kgs_username = models.CharField(max_length=10, blank=True)
    ogs_username = models.CharField(max_length=40, blank=True)
    ogs_id = models.PositiveIntegerField(default=0, blank=True, null=True)
    bio = MarkupTextField(
            blank=True, null=True,
            validators=[validators.NullableMaxLengthValidator(2000)]
    )
    p_status = models.PositiveSmallIntegerField(default=0)
    last_kgs_online = models.DateTimeField(blank=True, null=True)
    timezone = models.CharField(
        max_length=100,
        choices=[(t, t) for t in pytz.common_timezones],
        blank=True, null=True
    )
    start_cal = models.PositiveSmallIntegerField(default=0)
    end_cal = models.PositiveSmallIntegerField(default=24)

    def __str__(self):
        return self.user.username


class Division(models.Model):
    league_event = models.ForeignKey('LeagueEvent')
    name = models.TextField(max_length=20)
    order = models.SmallIntegerField(default=0)

    class Meta:
        unique_together = ('league_event', 'order',)
        ordering = ['-league_event', 'order']

    def __str__(self):
        return self.name

    def number_games(self):
        return self.sgf_set.distinct().count()

    def get_players(self):
        return self.leagueplayer_set.all().order_by('-score')

    def number_players(self):
        return self.leagueplayer_set.count()

    def possible_games(self):
        n = self.number_players()
        return int(n * (n - 1) * self.league_event.nb_matchs / 2)

    def is_first(self):
        return not Division.objects.filter(
            league_event=self.league_event,
            order__lt=self.order
        ).exists()

    def is_last(self):
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
        sgfs = self.sgf_set.all()
        players = LeaguePlayer.objects.filter(division=self).prefetch_related('user__profile')
        # First create a list of players with extra fields
        results = []
        for player in players:
            player.n_win = 0
            player.n_loss = 0
            player.n_games = 0
            player.score = 0
            player.results = {}
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
                winner.results[loser.pk].append({'id': sgf.pk, 'r': 1})
            else:
                winner.results[loser.pk] = [{'id': sgf.pk, 'r': 1}]
            if winner.pk in loser.results:
                loser.results[winner.pk].append({'id': sgf.pk, 'r': 0})
            else:
                loser.results[winner.pk] = [{'id': sgf.pk, 'r': 0}]

        # now let's set the active flag
        min_matchs = self.league_event.min_matchs
        for player in players:
            player.is_active = player.n_games >= min_matchs

        results = sorted(
            results,
            key=attrgetter('score', 'n_games'),
            reverse=True
        )
        return results


class LeaguePlayer(models.Model):
    user = models.ForeignKey('User')
    kgs_username = models.CharField(max_length=20, default='')
    ogs_username = models.CharField(max_length=40, null=True, blank=True)
    event = models.ForeignKey('LeagueEvent')
    division = models.ForeignKey('Division')
    # p_status is deprecated, we now store that in player profile
    p_status = models.SmallIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'division',)

    def __str__(self):
        return str(self.pk) + self.kgs_username

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
            resultsDict[opponent.kgs_username].append(record)

        for sgf in white_sgfs:
            opponent = sgf.black
            won = sgf.winner == self.user
            record = {
                'id': sgf.pk,
                'r': 1 if won else 0
            }
            resultsDict[opponent.kgs_username].append(record)
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

class Game(models.Model):
    """This model is deprecated and should be deleted soon."""

    sgf = models.OneToOneField('Sgf')
    event = models.ForeignKey('LeagueEvent', blank=True, null=True)
    black = models.ForeignKey('LeaguePlayer',
                              related_name='black',
                              blank=True,
                              null=True)
    white = models.ForeignKey('LeaguePlayer',
                              related_name='white',
                              blank=True,
                              null=True)
    winner = models.ForeignKey('LeaguePlayer',
                               related_name='winner',
                               blank=True,
                               null=True)

    def __str__(self):
        return str(self.pk) + ': ' + self.black.kgs_username + ' vs ' + self.white.kgs_username

    @staticmethod
    def create_game(sgf):
        """Create a game related to the sgf.
        does NOT perform any check on the sgf. Just uses the league_valid flag
        Please use check_validity before calling this
        return true if successfully create a game, false otherwise"""

        # check if we already got a game with this sgf
        if (Game.objects.filter(sgf=sgf).exists() or
                not (sgf.league_valid) or
                (sgf.event is None)):
            return False
        event = sgf.event
        # check players before saving the game otherwise we can't delete it:
        # calling unscore will raise error.
        # I guess that's why they do db normalisation
        whites = LeaguePlayer.objects.filter(kgs_username__iexact=sgf.wplayer).filter(event=event)
        if len(whites) == 1:
            white = whites.first()
        else:
            return False
        blacks = LeaguePlayer.objects.filter(kgs_username__iexact=sgf.bplayer).filter(event=event)
        if len(blacks) == 1:
            black = blacks.first()
        else:
            return False
        game = Game()
        game.event = event
        game.sgf = sgf
        game.save()  # we need to save it to be able to add a OnetoOnefield
        game.black = black
        game.white = white
        game.save()
        # add the winner field and score the results :
        if sgf.result.find('B+') == 0:
            game.winner = blacks.first()
            game.winner.score_win()
            game.white.score_loss()
        elif sgf.result.find('W+') == 0:
            game.winner = whites.first()
            game.winner.score_win()
            game.black.score_loss()
        else:
            # this shouldn't work this delete() will call unscore who needs a winner field.
            game.delete()
            return False
        game.save()
        return True
