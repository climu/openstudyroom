from __future__ import absolute_import, unicode_literals

# pylint: disable=import-error,wildcard-import,unused-wildcard-import

from .base import *

DEBUG = False

with open('/etc/db_pass.txt') as f:
    DB_PASS = f.read().strip()
DATABASES = {
    'default': {
        'ENGINE' : 'django.db.backends.postgresql_psycopg2',
        'NAME' : 'openstudyroom',
        'USER': 'osr',
        'PASSWORD' : DB_PASS,
        'HOST': 'localhost',
        'PORT': '',
    }
}

ALLOWED_HOSTS = ['openstudyroom.org', 'dev.openstudyroom.org']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format' : "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt' : "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'mysite.log',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'django': {
            'handlers':['file'],
            'propagate': True,
            'level':'DEBUG',
        },
        'MYAPP': {
            'handlers': ['file'],
            'level': 'DEBUG',
        },
    }
}

DJANGO_CRON_DELETE_LOGS_OLDER_THAN = 7

with open('/etc/secret_key.txt') as f:
    SECRET_KEY = f.read().strip()

with open('/etc/gmail_pass.txt') as f:
    GMAIL_PASS = f.read().strip()
EMAIL_USE_TLS = True
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_PASSWORD = GMAIL_PASS
EMAIL_HOST_USER = 'openstudyroom@gmail.com'
EMAIL_PORT = 587
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
