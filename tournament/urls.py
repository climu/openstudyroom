from django.conf.urls import url

from . import views

urlpatterns = [
    url(
        r'^create/$',
        views.TournamentCreate.as_view(success_url='/league/admin/events/'),
        name='create'
    ),
    url(
        r'^list/$',
        views.tournament_list,
        name='list'
    ),
    url(
        r'^(?P<tournament_id>[0-9]+)/settings/$',
        views.tournament_manage_settings,
        name='tournament_manage_settings'
    ),
    url(
        r'^(?P<tournament_id>[0-9]+)/groups/$',
        views.tournament_manage_groups,
        name='tournament_manage_groups'
    ),
    url(
        r'^invite/(?P<tournament_id>[0-9]+)$',
        views.tournament_invite_user,
        name='tournament_invite_user'
    ),
    url(
        r'^quit/(?P<tournament_id>[0-9]+)/(?P<player_id>[0-9]+)/$',
        views.tournament_remove_player,
        name='tournament_remove_player'
    ),
    url(
        r'^save_players_order/(?P<tournament_id>[0-9]+)/$',
        views.save_players_order,
        name='save_players_order'
    ),
    url(
        r'^create-group/(?P<tournament_id>[0-9]+)/$',
        views.create_group,
        name='create_group'
    ),
    url(
        r'^save-groups/(?P<tournament_id>[0-9]+)/$',
        views.save_groups,
        name='save_groups'
    ),
]
