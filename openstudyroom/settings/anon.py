# pylint: disable=wildcard-import,unused-wildcard-import
import os
from .local import *

DATABASES = {
    'default': {
        'ENGINE' : 'django.db.backends.postgresql_psycopg2',
        'NAME' : 'openstudyroom',
        'USER': 'osr',
        'PASSWORD' : 'osr',
        'HOST': 'localhost',
        'PORT': '',
    }
}
