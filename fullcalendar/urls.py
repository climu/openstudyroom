from django.conf.urls import url
from django.core.urlresolvers import reverse
from . import views

urlpatterns = [
    url(r'^update/(?P<pk>[0-9]+)/$', views.PublicEventUpdate.as_view(success_url='/calendar/admin/event-list/'), name='update_cal_event' ),
    url(r'^delete/(?P<pk>[0-9]+)/$', views.admin_delete_event, name='admin_delete_event' ),

    url(r'^create/$', views.PublicEventCreate.as_view(success_url='/calendar/admin/event-list/'), name='create_cal_event' ),
    url(r'^$', views.calendar_view, name='calendar_view' ),
    url(r'^admin/event-list/$', views.admin_cal_event_list, name='admin_cal_event_list' ),
    url(r'^save/$', views.save, name='save' ),
    url(r'^json-feed/$', views.json_feed, name='json_feed' ),
    url(r'^create-game-request/$', views.create_game_request, name='create_game_request' ),

]
