from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.conf import settings


@shared_task(bind=True, retry_backoff=True, max_retries=10)
def kgs_connect(self):
    """Connect to KGS server and retunr cookie.
        Could we consider using redis memory db to store this cookie somehow?
    """
    url = 'http://www.gokgs.com/json/access'
    # If you are running this locally and want to run scraper, you should use your own
    # KGS credential
    if settings.DEBUG:
        kgs_password = 'yourpassword' # change this for local test
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
