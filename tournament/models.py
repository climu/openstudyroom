''' Implement bracket tournament models to send it to the jQuery Bracket library.
http://www.aropupu.fi/bracket/
This is heavily inspire from https://github.com/kevinharvey/django-tourney and musniro work.
'''

from django.db import models

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
    order = models.PositiveSmallIntegerField()



class Match(models.Model):
    """ A tournament match"""
    sgf = models.ForeignKey(Sgf, blank=True, null=True)
    bracket = models.ForeignKey(Bracket, blank=True, null=True)
    player_1 = models.ForeignKey(LeaguePlayer, null=True, related_name="player_1_match")
    player_2 = models.ForeignKey(LeaguePlayer, null=True, related_name="player_2_match")
    round = models.PositiveSmallIntegerField()
    round_index = models.PositiveSmallIntegerField()
