# pylint: disable=wildcard-import,unused-wildcard-import
import os
from .base import *


DEBUG = True

# for discord testing api without https
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

INSTALLED_APPS += [
    'debug_toolbar',
]

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
]

SECRET_KEY = 'yourlocalsecretkey'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DISCORD_CLIENT_ID = "xxxxxxxxxxxxxxxxx"
DISCORD_CLIENT_SECRET = "xxxxxxxxxxxxxxxxxx"
