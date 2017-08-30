from django.conf.urls import url
from django.core.urlresolvers import reverse
from . import views

urlpatterns = [

    url(r'^admin/list/$', views.admin_community_list, name='admin_community_list'),
    url(r'^admin/create/$', views.admin_community_create, name='admin_community_create'),
    url(r'^admin/delete/(?P<pk>[0-9]+)/$', views.admin_community_delete, name='admin_community_delete'),

    url(
        r'^update/(?P<pk>[0-9]+)/$',
        views.CommunityUpdate.as_view(success_url='/'),
        name='admin_community_update'
    ),
]
