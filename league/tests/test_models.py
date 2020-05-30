import pytest

from league import models


@pytest.mark.django_db
class TestSgfModel:
    def test_get_players(
        self,
        cho_chikun,
        kobayashi_koichi,
        sgf_text,
        league_event,
    ):
        b = models.LeaguePlayer.objects.create(
            user=cho_chikun,
            kgs_username='nomeNEST',
            event=league_event,
        )
        w = models.LeaguePlayer.objects.create(
            user=kobayashi_koichi,
            kgs_username='climu',
            event=league_event,
        )
        sgf_m = models.Sgf.objects.create(p_status=2, sgf_text=sgf_text)
        sgf_m.parse()
        black, white = sgf_m.get_players(league_event)
        assert black == b and white == w


@pytest.mark.django_db
class TestUserModel:
    def test_check_ogs(self, cho_chikun, requests_mock, ogs_response):
        expected_url = f"https://online-go.com/api/v1/players/{cho_chikun.profile.ogs_id}/games/"
        requests_mock.get(expected_url, json=ogs_response)
        cho_chikun.check_ogs([])
        assert requests_mock.called
