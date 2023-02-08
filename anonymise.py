import anon
import sys
from anon import lazy_attribute
from django.conf import settings
from league.models import User, Profile
from allauth.account.models import EmailAddress
from discord_bind.models import DiscordUser
from faker import Faker
from django.contrib.admin.models import LogEntry
from django_comments.models import Comment
from django_comments_xtd.models import Comment as CommentXtd
from django.contrib.sessions.models import Session
from postman.models import Message

fake = Faker()
Faker.seed(0)

"""
Anonymise production database.
We keep only datas that are publicly available on OSR website allready.
Admin forum have been removed by hand.

"""

# Prevent from running on production, just in case.
if not settings.DEBUG:
    print("What the hell are you thinking?!!!!")
    sys.exit()


class UserAnonymizer(anon.BaseAnonymizer):
    """Anonymise league.user:
        - email
        - last_login:  keep year and set day and month to 1
        - password to pass
        - date_joined: keep year and set day and month to 1
        - first_name
        - last_name
    Two users were able to enter their first and last name into the database. I don't know how!
    We keep username
    """
    email = anon.fake_email

    @lazy_attribute
    def last_login(self):
        # keep year
        return self.last_login.replace(day=1, month=1)

    @lazy_attribute
    def date_joined(self):
        # keep year
        return self.date_joined.replace(day=1, month=1)

    @lazy_attribute
    def first_name(self):
        if self.first_name:
            return anon.fake_name(max_size=15)
        return ''

    @lazy_attribute
    def last_name(self):
        if self.last_name:
            return anon.fake_name(max_size=15)
        return ''

    def clean(self, obj):
        obj.set_password('pass')
        obj.save()

    class Meta:
        model = User


class EmailAnonymizer(anon.BaseAnonymizer):
    email = anon.fake_email

    class Meta:
        model = EmailAddress


class DiscordUserlAnonymizer(anon.BaseAnonymizer):
    email = anon.fake_email
    access_token = ''
    refresh_token = ''
    expiry = fake.date_time_this_decade

    class Meta:
        model = DiscordUser


class ProfileAnonymizer(anon.BaseAnonymizer):
    """Only non public profile infos are calendar settings"""
    start_cal = 0
    end_cal = 24

    class Meta:
        model = Profile


def rm_django_admin_logs():
    LogEntry.objects.all().delete()


def rm_comments():
    Comment.objects.all().delete()
    CommentXtd.objects.all().delete()


def rm_sessions():
    Session.objects.all().delete()


def rm_messages():
    Message.objects.all().delete()


# UserAnonymizer().run()
# EmailAnonymizer().run()
# DiscordUserlAnonymizer().run()
# ProfileAnonymizer().run()
# rm_django_admin_logs()
# rm_comments()
# rm_sessions()
rm_messages()
