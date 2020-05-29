import freezegun
import pytest


FROZEN_TIME = '2020-05-29T11:14:00'


@pytest.fixture(autouse=True)
def freeze_time():
    with freezegun.freeze_time(FROZEN_TIME):
        yield


from league.fixtures.pytest_fixtures import *
