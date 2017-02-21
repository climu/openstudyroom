from __future__ import absolute_import, unicode_literals

from .base import *
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# SECURITY WARNING: keep the secret key used in production secret!
with open('/etc/secret_key.txt') as f:
    SECRET_KEY = f.read().strip()


EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


