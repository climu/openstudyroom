import pytz
from django.db import models
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.conf.global_settings import LANGUAGES
from machina.models.fields import MarkupTextField
from machina.core import validators

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
