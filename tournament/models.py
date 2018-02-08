''' Implement bracket tournament models to send it to the jQuery Bracket library.
http://www.aropupu.fi/bracket/
This is heavily inspire from https://github.com/kevinharvey/django-tourney and musniro work.
'''

from django.db import models
from collections import defaultdict
from league.models import LeagueEvent, LeaguePlayer, Sgf, Division


# Create your models here.
class Tournament(LeagueEvent):
    """ A Tournament is an interface to LeagueEvent
    """

    def __init__(self, *args, **kwargs):
        LeagueEvent.__init__(self, *args, **kwargs)
        self.type = 'tournament'

    def last_player_order(self):
        last_player = TournamentPlayer.objects.filter(event=self).order_by('order').last()
        if last_player is None:
            return 0
        else:
            return last_player.order

    def last_bracket_order(self):
        """ Return the last bracket order."""
        last_bracket = Bracket.objects.filter(tournament=self).order_by('order').last()
        if last_bracket is None:
            return 0
        else:
            return last_bracket.order

class TournamentPlayer(LeaguePlayer):
    order = models.PositiveSmallIntegerField()


class TournamentGroup(Division):

    def get_tournament_players(self):
        """Return an ordered list of 4 players of this group.
        If the group has less than 4 players, we fill it with None
        """
        players = list(TournamentPlayer.objects.filter(division=self).order_by('order'))
        return players



class Bracket(models.Model):
    tournament = models.ForeignKey(Tournament, null=True)
    order = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return self.tournament.name + " " + str(self.order)

    def get_rounds(self):
        return self.round_set.all()

    def generate_bracket(self):
        """Create a small 2 round bracket matches"""
        round = Round.objects.create(bracket=self, order=0)
        Match.objects.create(bracket=self, round=round, order=0)
        Match.objects.create(bracket=self, round=round, order=1)
        round = Round.objects.create(bracket=self, order=1)
        Match.objects.create(bracket=self, round=round, order=0)


class Round(models.Model):
    """A tournament round."""
    bracket = models.ForeignKey(Bracket, blank=True, null=True)
    order = models.PositiveSmallIntegerField()

    def __str__(self):
        return self.bracket.tournament.name + " " + str(self.bracket.order) + "/" + str(self.order)

    def get_matchs(self):
        return self.match_set.all()

class Match(models.Model):
    """ A tournament match"""
    sgf = models.ForeignKey(Sgf, blank=True, null=True)
    bracket = models.ForeignKey(Bracket, blank=True, null=True)
    round = models.ForeignKey(Round, blank=True, null=True)
    player_1 = models.ForeignKey(LeaguePlayer, blank=True, null=True, related_name="player_1_match")
    player_2 = models.ForeignKey(LeaguePlayer, blank=True, null=True, related_name="player_2_match")
    order = models.PositiveSmallIntegerField()
