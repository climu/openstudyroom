from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import Profile
import requests
import json

@shared_task
def kgs_update_online():
    chain = kgs_connect.s() | kgs_update_online_with_cookies.s()
    chain()


@shared_task(bind=True, retry_backoff=True, max_retries=10)
def kgs_connect(self):
    """Connect to KGS server and retunr cookie.
        Could we consider using redis memory db to store this cookie somehow?
    """

    url = 'http://www.gokgs.com/json/access'
    # If you are running this locally, you should use your own
    # KGS credential
    if settings.DEBUG:
        kgs_password = 'mypasword' # change this for local test
    else:
        with open('/etc/kgs_password.txt') as f:
            kgs_password = f.read().strip()

    message = {
        "type": "LOGIN",
        "name": "OSR", # change this if you are testing locally
        "password": kgs_password,
        "locale": "en_US",
    }
    formatted_message = json.dumps(message)
    response = requests.post(url, formatted_message)

    if response.status_code == 200:
        return response.cookies
    else:
        raise self.retry()


@shared_task(bind=True, retry_backoff=True, max_retries=10)
def kgs_update_online_with_cookies(self, cookies):
    """Update profiles of users connected to KGS."""

    url = 'http://www.gokgs.com/json/access'
    response = requests.get(url, cookies=cookies)
    if response.status_code == 200:
        now = timezone.now()
        for m in json.loads(response.text)['messages']:
            if m['type'] == 'ROOM_JOIN' and m['channelId'] == 3627409:
                for kgs_user in m['users']:
                    osr_profile = Profile.objects.filter(
                        kgs_username__iexact=kgs_user['name']).first()
                    if osr_profile is not None:
                        osr_profile.last_kgs_online = now
                        osr_profile.save()
                break
    else:
        self.retry()


@shared_task
def test_task():
    print('testing')
    return 'testing'
