from django.conf.urls import url
from django.core.urlresolvers import reverse
from . import views

urlpatterns = [
    url(
        r'^(?P<name>[\w.@+-]+)/$',
        views.community_page,
        name='community_page'
    ),
    url(
        r'^admin/list/$',
        views.admin_community_list,
        name='admin_community_list'
    ),
    url(
        r'^admin/create/$',
        views.admin_community_create,
        name='admin_community_create'
    ),
    url(
        r'^admin/delete/(?P<pk>[0-9]+)/$',
        views.admin_community_delete,
        name='admin_community_delete'
    ),
    url(
        r'^admin/update/(?P<pk>[0-9]+)/$',
        views.AdminCommunityUpdate.as_view(success_url='/community/admin/list/'),
        name='admin_community_update'
    ),
    url(
        r'^update/(?P<pk>[0-9]+)/$',
        views.CommunityUpdate.as_view(),
        name='community_update'
    ),
    url(
        r'^(?P<community_pk>[0-9]+)/create-league/$',
        views.community_create_league,
        name='create_league'
    ),
]
