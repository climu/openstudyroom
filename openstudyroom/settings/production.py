from __future__ import absolute_import, unicode_literals

# pylint: disable=import-error,wildcard-import,unused-wildcard-import

from .base import *

DEBUG = False

try:
    from .local import *
except ImportError:
    pass
