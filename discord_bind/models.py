'''

The MIT License (MIT)

Copyright (c) 2016, Mark Rogaski

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

'''
from __future__ import unicode_literals

import logging

import requests
from django.conf import settings as django_settings
from django.contrib.auth.models import Group
from django.db import models

from discord_bind.conf import settings

logger = logging.getLogger(__name__)


class DiscordUser(models.Model):
    """ Discord User mapping. """
    user = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='discord_user',
    )
    uid = models.CharField(max_length=20, blank=False, unique=True)
    username = models.CharField(max_length=254)
    discriminator = models.CharField(max_length=4)
    avatar = models.CharField(max_length=32, blank=True)
    email = models.EmailField(max_length=254, blank=True)
    access_token = models.CharField(max_length=32, blank=True)
    refresh_token = models.CharField(max_length=32, blank=True)
    scope = models.CharField(max_length=256, blank=True)
    expiry = models.DateTimeField(null=True)
    status = models.CharField(max_length=256, blank=True)
    def __str__(self):
        return self.username + '.' + self.discriminator


class DiscordInvite(models.Model):
    """ Discord instant invites """
    TEXT = 'text'
    VOICE = 'voice'
    CHANNEL_TYPE_CHOICES = (
        (TEXT, 'text'),
        (VOICE, 'voice'),
    )

    code = models.CharField(max_length=32, unique=True)
    active = models.BooleanField(default=False)
    groups = models.ManyToManyField(Group, blank=True,
                                    related_name='discord_invites')
    description = models.CharField(max_length=256, blank=True)
    guild_name = models.CharField(max_length=64, blank=True)
    guild_id = models.CharField(max_length=20, blank=True)
    guild_icon = models.CharField(max_length=32, blank=True)
    channel_name = models.CharField(max_length=64, blank=True)
    channel_id = models.CharField(max_length=20, blank=True)
    channel_type = models.CharField(max_length=5, blank=True,
                                    choices=CHANNEL_TYPE_CHOICES)

    def __str__(self):
        return self.code

    def update_context(self):
        result = False
        r = requests.get(settings.DISCORD_BASE_URI + '/invites/' + self.code)
        if r.status_code == 200:
            invite = r.json()
            try:
                self.guild_name = invite['guild']['name']
                self.guild_id = invite['guild']['id']
                self.guild_icon = invite['guild']['icon']
                self.channel_name = invite['channel']['name']
                self.channel_id = invite['channel']['id']
                self.channel_type = invite['channel']['type']
                self.save()
                result = True
            except KeyError:
                pass

        return result
