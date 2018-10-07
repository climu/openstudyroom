from django.db import models
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from machina.models.fields import MarkupTextField
from machina.core import validators

class Community(models.Model):

    name = models.CharField(max_length=20, blank=True, unique=True)
    slug = models.CharField(max_length=5, blank=True, unique=True)
    admin_group = models.ForeignKey(Group, related_name='admin_community', on_delete=models.CASCADE)
    user_group = models.ForeignKey(Group, null=True, blank=True, related_name='user_community', on_delete=models.CASCADE)
    close = models.BooleanField(default=False)
    private = models.BooleanField(default=False)
    promote = models.BooleanField(default=False)
    description = MarkupTextField(
        blank=True, null=True,
        validators=[validators.NullableMaxLengthValidator(2000)])
    private_description = MarkupTextField(
        blank=True, null=True,
        validators=[validators.NullableMaxLengthValidator(2000)])


    def __str__(self):
        return self.name

    @classmethod
    def create(cls, name, slug):
        '''We create the admin and users group before creating the community object'''

        if not Group.objects.filter(name=slug + '_community_admin').exists():
            admin_group = Group.objects.create(name=slug + '_community_admin')

        if not Group.objects.filter(name=slug + '_community_member').exists():
            user_group = Group.objects.create(name=slug + '_community_member')

        # else we should return an error:'group already here'
        community = cls(
            name=name,
            slug=slug,
            admin_group=admin_group,
            user_group=user_group
        )
        return community

    def get_admins(self):
        User = get_user_model()
        return list(User.objects.filter(groups=self.admin_group))

    def is_admin(self, user):
        admin = user.is_authenticated and (
            user.is_league_admin() or
            self.admin_group in user.groups.all()
        )
        return admin

    def is_member(self, user):
        return user in self.user_group.user_set.all()
