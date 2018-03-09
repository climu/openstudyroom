"""Some utils."""
from django.shortcuts import get_object_or_404
from .models import Match, TournamentPlayer


def save_round(round, matches):
    """Just to avoid nested loops"""
    for match_id, players in matches.items():
        match = get_object_or_404(Match, pk=match_id, round=round)
        if match.sgf is None:
            if len(players) > 0:
                player_1 = get_object_or_404(TournamentPlayer, pk=players[0], event=round.bracket.tournament)
                match.player_1 = player_1
                match.player_2 = None
                if len(players) == 2:
                    player_2 = get_object_or_404(TournamentPlayer, pk=players[1], event=round.bracket.tournament)
                    match.player_2 = player_2
                if len(players) < 3:
                    match.save()
            else:
                match.player_1 = None
                match.player_2 = None
                match.save()
    return
