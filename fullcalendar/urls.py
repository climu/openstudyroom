from django.conf.urls import url
from django.core.urlresolvers import reverse
from . import views

urlpatterns = [
    url(
        r'^update/(?P<pk>[0-9]+)/$',
        views.PublicEventUpdate.as_view(success_url='/calendar/admin/event-list/'),
        name='update_cal_event'
    ),
    url(
        r'^delete/(?P<pk>[0-9]+)/$',
        views.admin_delete_event,
        name='admin_delete_event'
    ),

    url(
        r'^create/$',
        views.PublicEventCreate.as_view(success_url='/calendar/admin/event-list/'),
        name='create_cal_event'
    ),
    url(r'^$', views.calendar_view, name='calendar_view'),
    url(
        r'^(?P<user_id>[0-9]+)/$',
        views.calendar_view,
        name='calendar_view'
    ),
    url(
        r'^admin/event-list/$',
        views.admin_cal_event_list,
        name='admin_cal_event_list'
    ),
    url(r'^save/$', views.save, name='save'),
    url(r'^json-feed/$', views.json_feed, name='json_feed'),
    url(
        r'^json-feed/(?P<user_id>[0-9]+)/$',
        views.json_feed_other,
        name='json_feed_other'
    ),
    url(
        r'^create-game-request/$',
        views.create_game_request,
        name='create_game_request'
    ),
    url(
        r'^cancel-game-request-ajax/$',
        views.cancel_game_request_ajax,
        name='cancel_game_request_ajax'
    ),
    url(
        r'^reject-game-request-ajax/$',
        views.reject_game_request_ajax,
        name='reject_game_request_ajax'
    ),
    url(
        r'^accept-game-request-ajax/$',
        views.accept_game_request_ajax,
        name='accept_game_request_ajax'
    ),
    url(
        r'^cancel-game-ajax/$',
        views.cancel_game_ajax,
        name='cancel_game_ajax'
    ),
    url(
        r'^update-time-range-ajax/$',
        views.update_time_range_ajax,
        name='update_time_range_ajax'
    ),
    url(
        r'^copy-previous-week-ajax/$',
        views.copy_previous_week_ajax,
        name='copy_previous_week_ajax'
    ),
]
