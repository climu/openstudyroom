''' Implement bracket tournament models to send it to the jQuery Bracket library.
http://www.aropupu.fi/bracket/
This is heavily inspire from https://github.com/kevinharvey/django-tourney and musniro work.
'''

from django.db import models
from league.models import LeagueEvent, LeaguePlayer, Sgf, Division
from machina.models.fields import MarkupTextField
from machina.core import validators
from fullcalendar.models import PublicEvent

# Create your models here.
class Tournament(LeagueEvent):
    """ A Tournament is an interface to LeagueEvent
    stage is the stage of the tournament:
    - 0: tournament is close
    - 1: group stage
    - 2: bracket stage
    """
    stage = models.PositiveSmallIntegerField(default=0)
    about = MarkupTextField(
            blank=True, null=True,
            validators=[validators.NullableMaxLengthValidator(5000)]
    )
    rules = MarkupTextField(
            blank=True, null=True,
            validators=[validators.NullableMaxLengthValidator(5000)]
    )
    use_calendar = models.BooleanField(default=True)
    winner = models.ForeignKey(
        'league.User',
        null=True,
        blank=True,
        related_name="won_tournament",
        on_delete=models.CASCADE
    )

    def last_player_order(self):
        last_player = TournamentPlayer.objects.filter(event=self).order_by('order').last()
        if last_player is None:
            return 0
        else:
            return last_player.order

    def last_bracket_order(self):
        """Return the last bracket order."""
        last_bracket = Bracket.objects.filter(tournament=self).order_by('order').last()
        if last_bracket is None:
            return 0
        else:
            return last_bracket.order


    def check_sgf_validity(self, sgf):
        """Check if a sgf is valid for a tournament.

        return a dict as such:
        """
        out = {
            'valid': False,
            'message': 'Tournament is closed',
            'group': None,
            'match': None
        }
        if self.stage == 0:
            return out

        settings = sgf.check_event_settings(self)

        if not settings['valid']:
            out.update({'message': settings['message']})
        elif self.stage == 1:
            group = sgf.check_players(self)
            if group['valid']:
                out.update({
                    'valid': True,
                    'group': group['division']
                })
            else:
                out.update({'message': group['message']})

        elif self.stage == 2:
            [bplayer, wplayer] = sgf.get_players(self)

            if wplayer is not None and bplayer is not None:
                bplayer = TournamentPlayer(pk=bplayer.pk)
                wplayer = TournamentPlayer(pk=wplayer.pk)
                match = wplayer.can_play_in_brackets(bplayer)
                if match is not None:
                    out.update({
                        'valid': True,
                        'match': match,
                        'message': ''
                    })
                else:
                    out.update({'message': '; Not a match'})
            else:
                out.update({'message': '; One of the player is not a league player'})
        else:
            out.update({'message': '; This tournament stage is wrong'})
        sgf.message = out['message']
        sgf.league_valid = out['valid']
        return out

    def get_formated_events(self, start, end, tz):
        """ return a dict of publics events between start and end formated for json."""

        public_events = self.tournamentevent_set.filter(end__gte=start, start__lte=end)

        data = []
        for event in public_events:
            dict = {
                'id': 'public:' + str(event.pk),
                'title': event.title,
                'description': event.description,
                'start': event.start.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                'end': event.end.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                'is_new': False,
                'editable': False,
                'type': 'public',
            }
            if event.url:
                dict['url'] = event.url
            data.append(dict)
        return data

class TournamentPlayer(LeaguePlayer):
    order = models.PositiveSmallIntegerField()

    def can_play_in_brackets(self, player):
        """Check if 2 players can play in the bracket stage.

        Return the corresponding match if it exists and None otherwise.
        """
        matchs = Match.objects.filter(player_1=self, player_2=player, winner=None)
        if len(matchs) > 0:
            return matchs.first()

        matchs = Match.objects.filter(player_1=player, player_2=self, winner=None)
        if len(matchs) > 0:
            return matchs.first()

        return None

class TournamentGroup(Division):

    def get_tournament_players(self):
        """Return an ordered list of 4 players of this group.
        If the group has less than 4 players, we fill it with None. Do we?
        """
        players = list(TournamentPlayer.objects.filter(division=self).order_by('order'))
        return players


class Bracket(models.Model):
    name = models.TextField(max_length=20, blank=True, null=True, default="")
    tournament = models.ForeignKey(Tournament, null=True, on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return self.tournament.name + " " + str(self.order)

    def get_rounds(self):
        return self.round_set.all().order_by('order')

    def create_round(self):
        order = self.round_set.all().order_by('order').last().order + 1
        round = Round.objects.create(bracket=self, order=order)
        Match.objects.create(bracket=self, round=round, order=0)
        return round

    def generate_bracket(self):
        """Create a small 2 round bracket matches."""
        round = Round.objects.create(bracket=self, order=0)
        Match.objects.create(bracket=self, round=round, order=0)
        Match.objects.create(bracket=self, round=round, order=1)
        round = Round.objects.create(bracket=self, order=1)
        Match.objects.create(bracket=self, round=round, order=0)



class Round(models.Model):
    """A tournament round."""
    name = models.TextField(max_length=20, blank=True, null=True, default="")
    bracket = models.ForeignKey(Bracket, blank=True, null=True, on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField()

    def __str__(self):
        return self.bracket.tournament.name + " " + str(self.bracket.order) + "/" + str(self.order)

    def get_matchs(self):
        return self.match_set.all().order_by('order')

    def create_match(self):
        last_match = self.match_set.all().order_by('order').last()
        if last_match:
            order = last_match.order + 1
        else:
            order = 0
        Match.objects.create(bracket=self.bracket, round=self, order=order)
        return self

    def delete_match(self):
        match = self.match_set.all().order_by('order').last()
        if match.player_1 or match.player_2:
            return
        else:
            match.delete()
            return


class Match(models.Model):
    """ A tournament match.

    A match can have a winner without a sgf if a player is seeded.
    """
    sgf = models.ForeignKey(
        Sgf,
        blank=True,
        null=True,
        on_delete=models.SET_NULL)
    bracket = models.ForeignKey(Bracket, blank=True, null=True, on_delete=models.CASCADE)
    round = models.ForeignKey(Round, blank=True, null=True, on_delete=models.CASCADE)
    player_1 = models.ForeignKey(TournamentPlayer, blank=True, null=True, related_name="player_1_match", on_delete=models.CASCADE)
    player_2 = models.ForeignKey(TournamentPlayer, blank=True, null=True, related_name="player_2_match", on_delete=models.CASCADE)
    winner = models.ForeignKey(TournamentPlayer, blank=True, null=True, related_name="winner_match", on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField()

    def __str__(self):
        out = str(self.round) + ": match " + str(self.order)
        if self.player_1:
            out += " " + self.player_1.user.username
        if self.player_2:
            out += " " + self.player_2.user.username

        return out

class TournamentEvent(PublicEvent):
    """ Public event related to a tournament."""
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE )

    def can_edit(self, user):
        return self.tournament.is_admin(user)
