import pytest

from league import models


@pytest.mark.django_db
class TestSgfModel:
    def test_get_players(self, sgf_text, league_event):
        b_u = models.User.objects.create(username='nomenest')
        w_u = models.User.objects.create(username='climu')
        b = models.LeaguePlayer.objects.create(user=b_u, kgs_username='nomeNEST', event=league_event)
        w = models.LeaguePlayer.objects.create(user=w_u, kgs_username='climu', event=league_event)
        sgf_m = models.Sgf.objects.create(p_status=2, sgf_text=sgf_text)
        sgf_m.parse()
        black, white = sgf_m.get_players(league_event)
        assert black == b and white == w


@pytest.mark.django_db
class TestUserModel:
    def test_check_ogs(self, requests_mock, ogs_response):
        user = models.User.objects.create(username='raylu')
        models.Profile.objects.create(user=user, ogs_id=106155)
        expected_url = f"https://online-go.com/api/v1/players/{user.profile.ogs_id}/games/"
        requests_mock.get(expected_url, json=ogs_response)
