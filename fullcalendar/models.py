import requests
from django.db import models
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from colorful.fields import RGBColorField
from pytz import utc

from league.models import User
from community.models import Community

class Category(models.Model):
    name = models.CharField(max_length=20)
    color = RGBColorField(null=True)
    community = models.ForeignKey(Community, blank=True, null=True, on_delete=models.CASCADE)

    def can_edit(self, user):
        if self.community is None:
            return user.is_authenticated and user.is_osr_admin()
        else:
            return self.community.is_admin(user)

    def __str__(self):
        return self.name

    def get_redirect_url(self):
        """
        Get the url to redirect with after editing or deleting the event
        """
        if self.community is None:
            return reverse('calendar:admin_cal_event_list')
        else:
            return reverse(
                'community:community_page',
                kwargs={'slug':self.community.slug}
            )

class CalEvent(models.Model):
    start = models.DateTimeField()
    end = models.DateTimeField()

    class Meta:
        abstract = True

    def format(self, type, tz):
        return {
            'pk': self.pk,
            'start': self.start.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
            'end': self.end.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
            'type': type,
        }

class PublicEvent(CalEvent):
    title = models.CharField(max_length=30)
    description = models.TextField(blank=True)
    url = models.URLField(blank=True)
    category = models.ForeignKey(Category, blank=True, null=True, on_delete=models.SET_NULL)
    community = models.ForeignKey(Community, blank=True, null=True, on_delete=models.CASCADE)

    def format(self, tz):
        event = super().format('public', tz)
        event['title'] = self.title
        event['description'] = self.description
        event['url'] = self.url
        event['color'] = self.category.color if self.category else ''
        event['community'] = self.community.name if self.community else ''
        return event

    def can_edit(self, user):
        if self.community is None:
            return user.is_authenticated and user.is_osr_admin()
        else:
            return self.community.is_admin(user)


    def get_redirect_url(self):
        """
        Get the url to redirect with after editing or deleting the event
        """
        if self.community is None:
            return reverse('calendar:admin_cal_event_list')
        else:
            return reverse(
                'community:community_page',
                kwargs={'slug':self.community.slug}
            )

    @staticmethod
    def get_future_public_events():
        """return a query of all future public events to a user."""
        now = timezone.now()
        public_events = PublicEvent.objects.filter(end__gte=now)
        return public_events

    @staticmethod
    def get_formated_public_event(start, end, tz, community_pk=None):
        """ return a dict of publics events between start and end formated for json."""
        public_events = PublicEvent.objects.filter(end__gte=start, start__lte=end)
        if community_pk is None:
            public_events = public_events.filter(community=None)
        else:
            community = Community.objects.get(pk=int(community_pk))
            public_events = public_events.filter(community=community)
        data = []
        for event in public_events:
            dict = {
                'id': 'public:' + str(event.pk),
                'title': event.title,
                'description': event.description,
                'start': event.start.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                'end': event.end.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                'is_new': False,
                'editable': False,
                'type': 'public',
                'color': str(event.category.color) if event.category else "#3a87ad"
            }
            if event.url:
                dict['url'] = event.url
            data.append(dict)
        return data

    @staticmethod
    def get_formated_events(start, end, tz):
        events = PublicEvent.objects.filter(
            end__gte=start,
            start__lte=end)
        return [event.format(tz) for event in events]

class AvailableEvent(CalEvent):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def format(self, tz):
        return super().format('user-available', tz)

    @staticmethod
    def get_formated_user_available_events(user, start, end, tz):
        events = AvailableEvent.objects.filter(
            user=user,
            end__gte=timezone.now(),
            start__lte=end)
        return [event.format(tz) for event in events]

    @staticmethod
    def get_formated_opponent_available_events(user, divisions):
        tz = user.get_timezone()
        result = []
        events = AvailableEvent.get_formated_other_available(user, divisions)
        for event in events:
            formated = {
                'start': event['start'].astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                'end': event['end'].astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'opponents-available',
                'opponents': event['users'],
            }
            result.append(formated)
        return result

    @staticmethod
    def get_formated_other_available(user, division_list=None, server_list=None):
        """Return the other-available events related to a user for the divisions
        in division_list

        First we create a changes list that contain dicts formated as such:
        {
            'time': datetime,
            'user': user,
            'type': 1 if the user becomes available 0 otherwise
        }
        Then we go over this changes list and create new events formated as such:
        {
            ‘start’:datetime,
            ‘end’: datetime,
            ‘users’: a list of users available at between start and end
        }
        """
        now = timezone.now()
        list_users = user.get_opponents(division_list, server_list)
        availables = AvailableEvent.objects.filter(
            end__gte=now,
            user__in=list_users
        )
        changes = []
        for event in availables:
            change = {
                'time': event.start,
                'user': event.user.username,
                'type': 1  # means the user becomes available
            }
            changes.append(change)
            change = {
                'time': event.end,
                'user': event.user.username,
                'type': 0  # means the user becomes unavailable
            }
            changes.append(change)
        changes = sorted(changes, key=lambda k: k['time'])

        events = []
        for idx, change in enumerate(changes):
            if idx == 0:
                time = change['time']
                list_users = [change['user']]
                continue

            if time == change['time']:
                # another change at the same moment.
                # We just add or remove a player
                if change['type'] == 1:  # user becomes available
                    list_users.append(change['user'])
                else:
                    list_users.remove(change['user'])
            else:
                if len(list_users) == 0:
                    if change['type'] == 1:
                        # we need to start a new event
                        time = change['time']
                        list_users.append(change['user'])
                else:
                    # we add the event to the events list
                    events.append({
                        'start': time,
                        'end': change['time'],
                        'users': list(list_users),
                    })
                    time = change['time']
                    if change['type'] == 0:  # new user available
                        list_users.remove(change['user'])
                    else:
                        list_users.append(change['user'])
        return events

    @staticmethod
    def format_me_availables(events, background, tz):
        formated_events = []

        for event in events:
            dict = {
                'id': 'me-a:' + str(event.pk),
                'pk': str(event.pk),
                'title': 'I am available',
                'start': event.start.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                'end': event.end.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                'is_new': False,
                'type': 'me-available',
                'color': '#ffff80',
                'className': 'me-available',
            }
            if background:
                dict['rendering'] = 'background'
            else:
                dict['editable'] = True

            formated_events.append(dict)

        return formated_events

    @staticmethod
    def annonce_on_discord(events):
        """Announce new available events on discord.

        events is a list of AvailableEvent all related to one single user.
        """
        if not events:
            return

        if settings.DEBUG:
            return
        else:
            with open('/etc/discord_calendar_hook_url.txt') as f:
                discord_url = f.read().strip()

        user = events[0].user.username
        title = "Plan your games!"
        content = "[" + user +"]" + "(https://openstudyroom.org/league/account/" + user +") wants to play:\n\n"
        for event in events:
            content += "- " + event.start.astimezone(utc).strftime("%d/%m %H:%M") +\
                " → " + event.end.astimezone(utc).strftime("%H:%M") + "\n"
        values = {
            "embeds": [{
                "title": title,
                "url": "https://openstudyroom.org/calendar/",
                "description": content,
                "footer":{
                "text": "All times in day/month format in 24h UTC time"
                }
            }]
        }
        r = requests.post(discord_url, json=values)
        r.raise_for_status()



class GameRequestEvent(CalEvent):
    sender = models.ForeignKey(
        User,
        related_name="%(app_label)s_%(class)s_related_sender",
        related_query_name="%(app_label)s_%(class)ss_sender",
        on_delete=models.CASCADE
    )
    receivers = models.ManyToManyField(
        User,
        related_name="%(app_label)s_%(class)s_related_receiver",
        related_query_name="%(app_label)s_%(class)ss_receiver",
    )

    def format_sender(self, tz):
        event = super().format('user-game-request', tz)
        event['receivers'] = [user.username for user in self.receivers.all()],
        return event

    def format_receiver(self, tz):
        event = super().format('opponent-game-request', tz)
        event['sender'] = self.sender.username,
        return event

    @staticmethod
    def get_formated_game_request_events(user, divisions, start, end, tz):
        formated_events = []
        now = timezone.now()
        opponents = user.get_opponents(divisions)
        user_requests = GameRequestEvent.objects.filter(
            sender=user,
            receivers__in=opponents,
            start__lte=end,
            end__gte=now,
        )
        opponent_requests = GameRequestEvent.objects.filter(
            sender__in=opponents,
            receivers=user,
            start__lte=end,
            end__gte=now,
        )
        formated_events += [event.format_sender(tz) for event in user_requests]
        formated_events += [event.format_receiver(tz) for event in opponent_requests]
        return formated_events

class GameAppointmentEvent(CalEvent):
    users = models.ManyToManyField(
        User,
        related_name="%(app_label)s_%(class)s_related",
        related_query_name="%(app_label)s_%(class)ss",
    )

    def __str__(self):
        return self.start.strftime("%x") + self.title()

    def title(self):
        users = self.users.all()
        return 'Game ' + users[0].username + ' vs ' + users[1].username

    def opponent(self, user):
        """Return the opponent of a game appointment"""
        return self.users.exclude(pk=user.pk).first()

    @staticmethod
    def get_future_games(user):
        """Return all the future game appointments for a user."""
        now = timezone.now()
        return user.fullcalendar_gameappointmentevent_related.filter(
            end__gte=now
        )

    @staticmethod
    def get_formated_game_appointments(user, now, tz):
        data = []
        game_appointments = user.fullcalendar_gameappointmentevent_related.filter(
            end__gte=now
        )
        for event in game_appointments:
            opponent = event.opponent(user)
            dict = {
                'id': 'game:' + str(event.pk),
                'pk': event.pk,
                'title': 'Game vs ' + opponent.username,
                'start': event.start.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                'end': event.end.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                'is_new': False,
                'editable': False,
                'type': 'game',
                'color': '#ff4444'
            }
            data.append(dict)

        return data

    @staticmethod
    def format_game_appointments(user, divisions, only_user, tz):
        formated_events = []
        now = timezone.now()
        user_appointments = GameAppointmentEvent.objects.filter(end__gte=now, users=user)
        for event in user_appointments:
            dict = {
                'pk': event.pk,
                'start': event.start.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                'end': event.end.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                'opponent': event.opponent(user).username,
                'type': 'user-game-appointment',
            }
            formated_events.append(dict)
        return formated_events
