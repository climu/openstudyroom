import requests
from colorful.fields import RGBColorField
from django.conf import settings
from django.db import models
from django.template import loader
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import activate, deactivate
from django.utils.translation import gettext as _
from postman.api import pm_broadcast, pm_write
from pytz import utc

from community.models import Community
from league.models import Division, User


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
    """Base class for calendar events"""
    start = models.DateTimeField()
    end = models.DateTimeField()

    class Meta:
        abstract = True

    def format(self, tz, type):
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

    def format(self, tz, type='public'):
        event = super().format(tz, type)
        event['title'] = self.title
        event['description'] = self.description
        event['url'] = self.url
        if self.category:
            event['color'] = self.category.color
        if self.community:
            event['community'] = self.community.format()
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
    def get_formated(start, end, tz):
        """
        Returns all public events.
        """
        events = PublicEvent.objects.filter(end__gte=start, start__lte=end)
        return [event.format(tz) for event in events]

class AvailableEvent(CalEvent):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def format(self, tz, type='available'):
        event = super().format(tz, type)
        event['user'] = {'name': self.user.username}
        return event

    @staticmethod
    def get_formated_user(user, end, tz):
        """
        Returns a list of all formated available events of a given user.
        """
        now = timezone.now()
        events = AvailableEvent.objects.filter(user=user, end__gte=now, start__lte=end)
        return [event.format(tz) for event in events]

    @staticmethod
    def get_formated_opponents(user, end, leagues=None):
        """
        The calendar sends a list of leagues.
        We get all related divisions then all user's opponents.

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
        divisions = Division.objects.filter(league_event__in=leagues)
        tz = user.get_timezone()
        now = timezone.now()
        opponents = user.get_opponents(divisions)
        availables = AvailableEvent.objects.filter(
            start__lte=end,
            end__gte=now,
            user__in=opponents
        )
        changes = []
        for event in availables:
            change = {
                'time': event.start,
                'user': {'name': event.user.username},
                'type': 1  # means the user becomes available
            }
            changes.append(change)
            change = {
                'time': event.end,
                'user': {'name': event.user.username},
                'type': 0  # means the user becomes unavailable
            }
            changes.append(change)
        changes = sorted(changes, key=lambda k: k['time'])

        events = []
        for idx, change in enumerate(changes):
            if idx == 0:
                time = change['time']
                opponents = [change['user']]
                continue

            if time == change['time']:
                # another change at the same moment.
                # We just add or remove a player
                if change['type'] == 1:  # user becomes available
                    opponents.append(change['user'])
                else:
                    opponents.remove(change['user'])
            else:
                if len(opponents) == 0:
                    if change['type'] == 1:
                        # we need to start a new event
                        time = change['time']
                        opponents.append(change['user'])
                else:
                    # we add the event to the events list
                    events.append({
                        'start': time.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                        'end': change['time'].astimezone(tz).strftime('%Y-%m-%d %H:%M:%S'),
                        'users': list(opponents),
                        'type': 'opponents-available',
                    })
                    time = change['time']
                    if change['type'] == 0:  # new user available
                        opponents.remove(change['user'])
                    else:
                        opponents.append(change['user'])
        return events
class GameRequestEvent(CalEvent):
    """
    Added 'private' and 'divisions' fields.
    Intended to be passed to the future GameAppointment event when
    receivers accept the request.
    """
    sender = models.ForeignKey(
        User,
        related_name='%(app_label)s_%(class)s_related_sender',
        related_query_name='%(app_label)s_%(class)ss_sender',
        on_delete=models.CASCADE
    )
    receivers = models.ManyToManyField(
        User,
        related_name='%(app_label)s_%(class)s_related_receiver',
        related_query_name='%(app_label)s_%(class)ss_receiver',
    )

    private = models.BooleanField(default=False)
    divisions = models.ManyToManyField(Division, blank=True)

    def format(self, tz, type='game-request'):
        event = super().format(tz, type)
        event['sender'] = {'pk': self.sender.pk, 'name': self.sender.username}
        event['private'] = self.private
        event['divisions'] = [div.format() for div in self.divisions.all()]
        event['receivers'] = [{'pk': user.pk, 'name': user.username} for user in self.receivers.all()]
        return event

    def notify_create(self, sender, receiver):
        """
        Called once at the creation of the game request.
        Sends a message to inform the receiver.
        """
        subject = 'Game request from ' + sender.username \
            + ' on ' + self.start.strftime('%d %b')
        plaintext = loader.get_template('fullcalendar/messages/game_request.txt')
        context = {
            'sender': sender,
            'date': self.start
        }
        message = plaintext.render(context)
        pm_broadcast(
            sender=sender,
            recipients=receiver,
            subject=subject,
            body=message,
            skip_notification=False
        )

    @staticmethod
    def get_formated(user, start, end, tz):
        """
        Returns all game request events related to a user.
        """
        formated_events = []
        now = timezone.now()
        events = GameRequestEvent.objects.filter(start__lte=end, end__gte=now)
        user_as_sender = events.filter(sender=user)
        user_as_receiver = events.filter(receivers=user)
        formated_events += [event.format(tz) for event in user_as_sender]
        formated_events += [event.format(tz) for event in user_as_receiver]
        return formated_events

    @staticmethod
    def create(sender, receiver, divisions, private, start, end):
        game_request = GameRequestEvent(start=start, end=end, sender=sender, private=private)
        game_request.save()
        game_request.receivers.add(receiver)
        game_request.divisions.add(*divisions)
        game_request.save()
        game_request.notify_create(sender, receiver)
        return game_request

class GameAppointmentEvent(CalEvent):
    users = models.ManyToManyField(
        User,
        related_name='%(app_label)s_%(class)s_related',
        related_query_name='%(app_label)s_%(class)ss',
    )
    private = models.BooleanField(default=False)
    divisions = models.ManyToManyField(Division, blank=True)

    def __str__(self):
        return self.start.strftime('%x') + self.title()

    def format(self, tz, type='game-appointment'):
        event = super().format(tz, type)
        event['divisions'] = [div.format() for div in self.divisions.all()]
        event['users'] = []
        event['private'] = self.private
        for user in self.users.all():
            # we dont use user.format because
            # we need minimal infos
            event['users'].append({
                'pk': user.pk,
                'name': user.username
            })
        return event

    def title(self):
        users = self.users.all()
        return 'Game ' + users[0].username + ' vs ' + users[1].username

    def opponent(self, user):
        """Return the opponent of a game appointment"""
        return self.users.exclude(pk=user.pk).first()

    def notify_create(self, sender, receiver, from_game_request):
        """
        Called once at the creation of the game appointment.
        Sends a message to inform the receiver.
        """
        if from_game_request is True:
            subject = receiver.username + ' has accepted your game request.'
            plaintext = loader.get_template('fullcalendar/messages/game_request_accepted.txt')
            context = {
                'user': receiver,
                'date': self.start
            }
            message = plaintext.render(context)
            pm_write(
                sender=receiver,
                recipient=sender,
                subject=subject,
                body=message,
                skip_notification=False
            )
        else:
            subject = sender.username + ' has planned a game appointment on ' + self.start.strftime('%d %b')
            plaintext = loader.get_template('fullcalendar/messages/game_appointment.txt')
            context = {
                'user': sender,
                'date': self.start
            }
            message = plaintext.render(context)
            pm_write(
                sender=sender,
                recipient=receiver,
                subject=subject,
                body=message,
                skip_notification=False
            )
        if self.private is not True:
            self.notify_on_discord(sender, receiver)

    def notify_on_discord(self, sender, receiver):
        # Get communities both users are in
        communities = list(set(sender.get_communities()) & set(receiver.get_communities()))
        for community in communities:
            if community.discord_webhook_url is not None:
                values = self.format_discord(community.get_timezone(), community.locale)
                r = requests.post(community.discord_webhook_url, json=values)
                r.raise_for_status()

    def format_discord(self, tz=utc, locale=None):
        """
        Makes a Discord's embed object from event's data.
        Optionnal timezone and locale can be used

        """
        date = timezone.localtime(self.start, tz).strftime('%d-%m-%Y %H:%M')
        title = 'New game planned !'
        divisions = []
        if locale:
            activate(locale)
            title = _('Game Appointment Created Title')
            deactivate()
        for division in self.divisions.all():
            divURI = settings.BASE_URL + f'/league/{division.league_event.pk}/results/{division.pk}'
            divisions.append(f'[{division.league_event.name} - {division.name}]({divURI})')
        leagueInfo = '' if not divisions else ', '.join(divisions)
        accountURI = settings.BASE_URL + reverse('league:league_account')
        players = ' vs '.join(f'**[{user.username}]({accountURI + user.username}/)**' for user in self.users.all())
        return {
            'embeds': [{
                'title': title,
                'description': f'{leagueInfo} \n\n {players} \n {date} ({tz})',
                'thumbnail': {
                    'url': 'https://sits-go.org/wp-content/uploads/2021/03/the-shell-16x4-1.jpg'
                }
            }]
        }

    @staticmethod
    def get_future_games(user):
        """Return all the future game appointments for a user."""
        now = timezone.now()
        return user.fullcalendar_gameappointmentevent_related.filter(
            end__gte=now
        )

    @staticmethod
    def get_formated(tz, user=None):
        """
        Game appointment are now considered as public event and
        therefore can be seen by anyone !
        They can be private if needed. If the user is authenticated
        also returns his privates events.
        """
        res = []
        now = timezone.now()
        events = GameAppointmentEvent.objects.filter(end__gte=now)
        res += [e.format(tz) for e in events.filter(private=False)]
        if user:
            res += [e.format(tz) for e in events.filter(private=True, users=user)]
        return res

    @staticmethod
    def create(sender, receiver, divisions, private, start, end, from_game_request=False):
        """
        Creates a new game appointment and send message to the receiver.
        'from_game_request' is true when the event is created from a game request.
        """
        game_appointment = GameAppointmentEvent(start=start, end=end, private=private)
        game_appointment.save()
        game_appointment.divisions.add(*divisions)
        game_appointment.users.add(receiver, sender)
        game_appointment.notify_create(sender, receiver, from_game_request)
        return game_appointment
