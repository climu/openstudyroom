''' Implement bracket tournament models to send it to the jQuery Bracket library.
http://www.aropupu.fi/bracket/
This is heavily inspire from https://github.com/kevinharvey/django-tourney and musniro work.
'''

from django.db import models
from collections import defaultdict
from operator import attrgetter
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
        sgfs = self.sgf_set.defer('sgf_text').all()
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

        # calulcate the sos for each player
        sos_matrix = [[0 for x in range(len(players)-1)] for y in range(len(players)-1)]
        pl_count = 0
        for player in players:
            sos = 0
            op_count = 0
            for opponent in player.results:
                sos += opponent.n_win
                sos_matrix[op_count][pl_count] = sos
                op_count += 1
            pl_count += 1

        results = sorted(
            results,
            key=attrgetter('score', 'n_games'),
            reverse=True
        )

        return results


class Bracket(models.Model):
    tournament = models.ForeignKey(Tournament, null=True)
    order = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return self.tournament.name + " " + str(self.order)

    def get_rounds(self):
        self.round_set.all()
        return self.round_set.all()

    def create_round(self):
        order = self.round_set.all().order_by('order').last().order + 1
        round = Round.objects.create(bracket=self, order=order)
        print(round)
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
    name = models.TextField(max_length=10, blank=True, null=True, default="")
    bracket = models.ForeignKey(Bracket, blank=True, null=True)
    order = models.PositiveSmallIntegerField()

    def __str__(self):
        return self.bracket.tournament.name + " " + str(self.bracket.order) + "/" + str(self.order)

    def get_matchs(self):
        return self.match_set.all()

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
    """ A tournament match"""
    sgf = models.ForeignKey(Sgf, blank=True, null=True)
    bracket = models.ForeignKey(Bracket, blank=True, null=True)
    round = models.ForeignKey(Round, blank=True, null=True)
    player_1 = models.ForeignKey(LeaguePlayer, blank=True, null=True, related_name="player_1_match")
    player_2 = models.ForeignKey(LeaguePlayer, blank=True, null=True, related_name="player_2_match")
    order = models.PositiveSmallIntegerField()
