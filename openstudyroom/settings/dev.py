from __future__ import absolute_import, unicode_literals

# pylint: disable=import-error,wildcard-import,unused-wildcard-import

from .base import *
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# SECURITY WARNING: keep the secret key used in production secret!
with open('/etc/secret_key.txt') as f:
    SECRET_KEY = f.read().strip()
