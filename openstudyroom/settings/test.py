from .base import *  # noqa: F403

# By default an in-memory sqlite DB is used
# This is slow to develop with since each test run needs to re-migrate
DATABASES['default']['TEST'] = { # noqa: F405
    'NAME': 'db_test.sqlite3',
}

DEBUG = True

SECRET_KEY = 'test'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DISCORD_CLIENT_ID = 'xxxxxxxxxxxxxxxxx'
DISCORD_CLIENT_SECRET = 'xxxxxxxxxxxxxxxxxx'

SITE_URL = 'http://test.test:8000'
