from django.conf.urls import url
from django.core.urlresolvers import reverse

from . import views

urlpatterns = [
    url(r'^$', views.event, name='event'),
    url(r'^results/$', views.results, name='results'),
    url(r'^meijin/$', views.meijin, name='meijin'),
    url(r'^ladder/$', views.ladder, name='ladder'),
    url(r'^admin/event/(?P<to_event_id>[0-9]+)/populate/$',
        views.populate, name='admin_event_populate'),
    url(r'^admin/event/(?P<to_event_id>[0-9]+)/populate/(?P<from_event_id>[0-9]+)/$',
        views.populate, name='admin_event_populate'),

    url(r'^admin/event/(?P<to_event_id>[0-9]+)/proceed-populate/(?P<from_event_id>[0-9]+)/$',
        views.proceed_populate, name='admin_proceed_populate'),
    url(r'^archives/$', views.archives, name='archives'),

    url(r'^(?P<event_id>[0-9]+)/results/(?P<division_id>[0-9]+)/$', views.results, name='results'),
    url(r'^(?P<event_id>[0-9]+)/results/$', views.results, name='results'),
    url(r'^(?P<event_id>[0-9]+)/$', views.event, name='event'),

    url(r'^games/$', views.games, name='games'),
    url(r'^games/(?P<sgf_id>[0-9]+)/$', views.games, name='game'),
    url(r'^(?P<event_id>[0-9]+)/games/$', views.games, name='games'),
    url(r'^(?P<event_id>[0-9]+)/games/(?P<sgf_id>[0-9]+)/$', views.games, name='game'),

    url(r'^players/$', views.players, name='players'),
    url(r'^(?P<event_id>[0-9]+)/players/$', views.players, name='players'),

    url(r'^discord/$', views.discord_redirect, name='discord_redirect'),

    url(r'^sgf/(?P<sgf_id>[0-9]+)/$', views.sgf, name='sgf'),
    url(r'^account/timezone/$', views.timezone_update, name='timezone_update'),


    url(r'^account/$', views.account, name='league_account'),
    url(r'^account/(?P<user_name>[\w.@+-]+)/$', views.account, name='league_account'),
    url(r'^scraper/$', views.scraper_view, name='scraper'),

    url(r'^admin/$', views.admin, name='admin'),
    url(r'^admin/sgf/(?P<sgf_id>[0-9]+)/$', views.admin_edit_sgf, name='edit_sgf'),
    url(r'^admin/handle-upload-sgf/$', views.handle_upload_sgf, name='handle_upload_sgf'),
    url(r'^admin/upload-sgf/$', views.upload_sgf, name='upload_sgf'),
    url(r'^admin/create-sgf/$', views.create_sgf, name='create_sgf'),

    url(r'^admin/events/$', views.admin_events, name='admin_events'),
    url(
        r'^admin/events/(?P<pk>[0-9]+)/$',
        views.LeagueEventUpdate.as_view(),
        name='admin_events_update'
    ),
    url(
        r'^admin/events/create/$',
        views.LeagueEventCreate.as_view(success_url='/league/admin/events/'),
        name='admin_events_create'
    ),
    url(r'^admin/events/(?P<event_id>[0-9]+)/set_primary/$',
        views.admin_events_set_primary, name='set_primary'),
    url(r'^admin/events/(?P<event_id>[0-9]+)/delete/$',
        views.admin_events_delete, name='delete_event'),
    url(r'^admin/sgf/$', views.admin_sgf_list, name='admin_sgf'),
    url(r'^admin/sgf/(?P<sgf_id>[0-9]+)/save/$', views.admin_save_sgf, name='save_sgf'),
    url(r'^admin/sgf/(?P<sgf_id>[0-9]+)/delete/$', views.admin_delete_sgf, name='delete_sgf'),
    url(r'^admin/events/(?P<event_id>[0-9]+)/create-division/$',
        views.admin_create_division, name='admin_create_division'),
    url(r'^admin/division/(?P<division_id>[0-9]+)/delete-division/$',
        views.admin_delete_division, name='admin_delete_division'),
    url(r'^admin/division/(?P<division_id>[0-9]+)/rename/$',
        views.admin_rename_division, name='admin_rename_division'),
    url(r'^admin/division/(?P<division_id>[0-9]+)/up-down/$',
        views.admin_division_up_down, name='admin_division_up_down'),
    url(r'^admin/users/$', views.admin_users_list, name='admin_users_list'),
    url(r'^admin/users/event/(?P<event_id>[0-9]+)/$',
        views.admin_users_list, name='admin_users_list'),
    url(r'^admin/users/event/(?P<event_id>[0-9]+)/division/(?P<division_id>[0-9]+)/$',
        views.admin_users_list, name='admin_users_list'),
    url(r'^admin/users/(?P<user_id>[0-9]+)/send-mail/$',
        views.admin_user_send_mail, name='admin_user_send_mail'),
    url(r'^scrap-list/$', views.scrap_list, name='scrap_list'),
    url(r'^scrap-list/(?P<profile_id>[0-9]+)/up/$', views.scrap_list_up, name='scrap_list_up'),
    url(r'^game/json/(?P<sgf_id>[0-9]+)/$', views.game_api, name='game_api'),
    url(r'^(?P<event_id>[0-9]+)/join/(?P<user_id>[0-9]+)/$', views.join_event, name='join_event'),
    url(r'^admin/create-all-profiles/$', views.create_all_profiles, name='create_all_profiles'),
    url(r'^admin/update-all-sgf-check-code/$',
        views.update_all_sgf_check_code, name='update_all_sgf_check_code'),
    url(r'^admin/update-all-sgf/$', views.update_all_sgf, name='update_all_sgf'),
    url(r'^admin/set-meijin/$', views.admin_set_meijin, name='set_meijin'),
]
