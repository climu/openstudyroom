from django.db import models
from league.models import LeagueEvent, User
from django.contrib.auth.models import Group

class Community(models.Model):

    name = models.CharField(max_length=20, blank=True, unique=True)
    admin_group = models.ForeignKey(Group, related_name='admin_community')
    user_group = models.ForeignKey(Group, null=True, blank=True, related_name='user_community')
    close = models.BooleanField(default=False)
    private = models.BooleanField(default=False)
    description = models.TextField(blank=True, max_length=100)

    def __str__(self):
        return self.name

    @classmethod
    def create(cls, name):
        '''We create the admin group before creating the guest object'''

        if not Group.objects.filter(name=name + '_community_admin').exists():
            group = Group.objects.create(name=name + '_community__admin')

        #else we should return an error:'group already here'
        community = cls(name=name, admin_group=group)
        return community

    def get_admins(self):
        return list(User.objects.filter(groups=self.admin_group))

class CommunityLeague(LeagueEvent):

    community = models.ForeignKey(Community)
