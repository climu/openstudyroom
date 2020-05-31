import pytest
from django.urls import reverse


@pytest.mark.usefixtures("registry")
@pytest.mark.django_db()
class TestGamesDatatableAPI:
    @pytest.fixture()
    def make_request(self, client):
        def _make_request(*args, **kwargs):
            url = reverse("league:games_api")
            return client.get(url, *args, **kwargs)
        return _make_request

    def test_with_no_sgfs(self, make_request):
        response = make_request()
        assert response.status_code == 200
        assert response.json() == {
            "data": [],
            "draw": 0,
            "recordsTotal": 0,
        }

    @pytest.mark.usefixtures("sgf_cho_vs_kobayashi")
    def test_with_sgf(
        self,
        make_request,
        snapshot,
    ):
        response = make_request()
        assert response.status_code == 200
        snapshot.assert_match(response.json())

    def test_league_dne(
        self,
        make_request,
    ):
        response = make_request(data={"league": "-1"})
        assert response.status_code == 404

    @pytest.mark.usefixtures("sgf_cho_vs_kobayashi")
    def test_with_league(
        self,
        make_request,
        league_event,
        snapshot,
    ):
        response = make_request(data={"league": league_event.pk})
        assert response.status_code == 200
        snapshot.assert_match(response.json())
