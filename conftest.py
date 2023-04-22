# ruff: noqa: F401
import freezegun
import pytest

from league.fixtures.pytest_fixtures import (
    cho_chikun,
    kobayashi_koichi,
    league_event,
    ogs_response,
    registry,
    sgf_cho_vs_kobayashi,
    sgf_text,
)

FROZEN_TIME = '2020-05-29T11:14:00'


@pytest.fixture(autouse=True)
def freeze_time():
    with freezegun.freeze_time(FROZEN_TIME):
        yield
