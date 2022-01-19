import pytz
from django.db import models
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.conf.global_settings import LANGUAGES
from machina.models.fields import MarkupTextField
from machina.core import validators
from league.go_federations import get_ffg_ladder, ffg_user_infos, ffg_rating2rank


class Community(models.Model):

    name = models.CharField(max_length=30, blank=True, unique=True)
    slug = models.CharField(max_length=8, unique=True)
    timezone = models.CharField(
        max_length=100,
        choices=[(t, t) for t in pytz.common_timezones],
        null=True,
        blank=True,
    )
    locale = models.CharField(
        max_length=100,
        choices=[(l[0], l[1]) for l in LANGUAGES],
        null=True,
        blank=True,
    )
    admin_group = models.ForeignKey(
        Group,
        related_name='admin_community',
        on_delete=models.CASCADE)
    user_group = models.ForeignKey(
        Group,
        null=True,
        blank=True,
        related_name='user_community',
        on_delete=models.CASCADE)
    new_user_group = models.ForeignKey(
        Group,
        null=True,
        blank=True,
        related_name='new_user_community',
        on_delete=models.CASCADE)
    close = models.BooleanField(default=False)
    private = models.BooleanField(default=False)
    promote = models.BooleanField(default=False)
    description = MarkupTextField(
        blank=True, null=True,
        validators=[validators.NullableMaxLengthValidator(4000)])
    private_description = MarkupTextField(
        blank=True, null=True,
        validators=[validators.NullableMaxLengthValidator(4000)])
    discord_webhook_url = models.URLField(blank=True, null=True)


    def __str__(self):
        return self.name

    def format(self):
        return {
            'pk': self.pk,
            'name': self.name,
        }

    def members(self):
        """
        Get the members of the league
        """
                # from league.models import User
        User = get_user_model()
        return User.objects.filter(groups=self.user_group).select_related('profile')

    def ranking(self,begin_time,end_time):
        """
        Retuern community league ranking dict
        """
        # get leagues
        leagues = self.leagueevent_set.all().\
            exclude(event_type='tournament').\
            filter(begin_time__gte=begin_time, end_time__lte=end_time)

        # get members
        members = self.members()

        # get ffg ladder
        ffg_ladder = get_ffg_ladder()

        # init the output data
        output = {
            'data':[]
        }

        # next, extend members properties with community related stats
        for idx, user in enumerate(members):
            ## dictionary returned
            this_user_data = {
                "full_name":user.get_full_name(),
                "games_count":0,
                "wins_count":0,
                "win_ratio":0.0,
                "idx":idx,
            }
            players = user.leagueplayer_set.all().filter(event__in=leagues)

            for player in players:
                this_user_data['wins_count'] += player.nb_win()
                this_user_data['games_count'] += player.nb_games()
            if this_user_data['games_count'] > 0:
                this_user_data['win_ratio'] = (this_user_data['wins_count'] * 100) / this_user_data['games_count']

            # ffg
            if user.profile.hasFfgLicenseNumber():
                rating = int(ffg_user_infos(user.profile.ffg_licence_number, ffg_ladder)['rating'])
                rank = ffg_rating2rank(rating)
                this_user_data['ffg_rating'] = rating
                this_user_data['ffg_rank'] = rank
                this_user_data['has_ffg_license'] = True
            else:
                this_user_data['ffg_rating'] = "N/A"
                this_user_data['ffg_rank'] = "N/A"
                this_user_data['has_ffg_license'] = False


            output['data'].append(this_user_data)
        return output


    @classmethod
    def create(cls, name, slug):
        '''We create the admin and users group before creating the community object'''

        if not Group.objects.filter(name=slug + '_community_admin').exists():
            admin_group = Group.objects.create(name=slug + '_community_admin')

        if not Group.objects.filter(name=slug + '_community_member').exists():
            user_group = Group.objects.create(name=slug + '_community_member')

        if not Group.objects.filter(name=slug + '_community_new_member').exists():
            new_user_group = Group.objects.create(name=slug + '_community_new_member')

        # else we should return an error:'group already here'
        community = cls(
            name=name,
            slug=slug,
            admin_group=admin_group,
            user_group=user_group,
            new_user_group=new_user_group
        )
        return community

    def get_admins(self):
        User = get_user_model()
        return list(User.objects.filter(groups=self.admin_group))

    def get_timezone(self):
        """Return the timezone of the community"""
        if self.timezone is not None:
            tz = pytz.timezone(self.timezone)
        else:
            tz = pytz.utc
        return tz

    def is_admin(self, user):
        return user.is_authenticated and self.admin_group in user.groups.all()

    def is_member(self, user):
        return user in self.user_group.user_set.all()
