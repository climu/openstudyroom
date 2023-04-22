import re

from django.conf.urls import url

from league.models import LeagueEvent

from . import views

# init urlpatterns
urlpatterns = []

# make the pattern for all the events
for (event_type, _) in LeagueEvent.EVENT_TYPE_CHOICES:
    new_pattern = [url(r'^' + re.escape(event_type) + r'/$',
                       views.get_first_league_event(event_type), name=event_type)]
    urlpatterns = urlpatterns + new_pattern

app_name = 'league'
urlpatterns = urlpatterns + [
    url(r'^$', views.division_results, name='results'),
    # Sad, but for historical reason, info page is named event.
    # If you want to replace reverses everywhere, be my guest
    url(r'^infos/$', views.infos, name='event'),
    url(r'^9x9/$', views.ninenine, name='ninenine'),

    url(r'^results/$', views.division_results, name='results'),

    url(r'^admin/event/(?P<to_event_id>[0-9]+)/populate/$',
        views.populate, name='admin_event_populate'),
    url(r'^admin/event/(?P<to_event_id>[0-9]+)/populate/(?P<from_event_id>[0-9]+)/$',
        views.populate, name='admin_event_populate'),

    url(r'^admin/event/(?P<to_event_id>[0-9]+)/proceed-populate/(?P<from_event_id>[0-9]+)/$',
        views.proceed_populate, name='admin_proceed_populate'),
    url(r'^archives/$', views.archives, name='archives'),

    url(r'^(?P<event_id>[0-9]+)/results/(?P<division_id>[0-9]+)/$',
        views.division_results, name='results'),
    url(r'^(?P<event_id>[0-9]+)/results/$',
        views.division_results, name='results'),
    url(r'^(?P<event_id>[0-9]+)/$', views.division_results, name='results'),
    url(r'^(?P<event_id>[0-9]+)/infos/$', views.infos, name='event'),
    url(r'^(?P<event_id>[0-9]+)/iframe/$',
        views.division_results_iframe, name='results_iframe'),
    url(r'^(?P<event_id>[0-9]+)/iframe/(?P<division_id>[0-9]+)/$',
        views.division_results_iframe, name='results_iframe'),

    url(r'^games/$', views.list_games, name='games'),
    url(r'^games/(?P<sgf_id>[0-9]+)/$', views.list_games, name='game'),
    url(r'^(?P<event_id>[0-9]+)/games/$', views.list_games, name='games'),
    url(r'^(?P<event_id>[0-9]+)/games/(?P<sgf_id>[0-9]+)/$',
        views.list_games, name='game'),

    url(r'^players/$', views.list_players, name='players'),
    url(r'^(?P<event_id>[0-9]+)/players/$',
        views.list_players, name='players'),

    url(r'^discord/$', views.discord_redirect, name='discord_redirect'),

    url(r'^sgf/(?P<sgf_id>[0-9]+)/$', views.download_sgf, name='sgf'),
    url(r'^all_sgf/(?P<user_id>[0-9]+)/$',
        views.download_all_sgf, name='all_sgf'),

    url(r'^account/timezone/$', views.timezone_update, name='timezone_update'),


    url(r'^account/$', views.account, name='league_account'),
    url(r'^account/(?P<user_name>[\w.@+-]+)/$',
        views.account, name='league_account'),
    url(r'^account/(?P<user_name>[\w.@+-]+)/activity/$',
        views.account_activity, name='league_account_activity'),
    url(r'^scraper/$', views.scraper_view, name='scraper'),

    url(r'^admin/$', views.admin, name='admin'),
    url(r'^admin/sgf/(?P<sgf_id>[0-9]+)/$',
        views.admin_edit_sgf, name='edit_sgf'),
    url(r'^admin/handle-upload-sgf/$',
        views.handle_upload_sgf, name='handle_upload_sgf'),
    url(r'^admin/handle-upload-sgf/(?P<tournament_id>[0-9]+)/$',
        views.handle_upload_sgf, name='handle_upload_sgf'),
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
    url(
        r'^admin/events/create/(?P<copy_from_pk>[0-9]+)/$',
        views.LeagueEventCreate.as_view(),
        name='admin_events_create'
    ),
    url(r'^admin/events/(?P<event_id>[0-9]+)/set_primary/$',
        views.admin_events_set_primary, name='set_primary'),
    url(r'^admin/events/(?P<event_id>[0-9]+)/delete/$',
        views.admin_events_delete, name='delete_event'),
    url(r'^admin/sgf/$', views.admin_sgf_list, name='admin_sgf'),
    url(r'^admin/sgf/(?P<sgf_id>[0-9]+)/save/$',
        views.admin_save_sgf, name='save_sgf'),
    url(r'^admin/sgf/(?P<sgf_id>[0-9]+)/delete/$',
        views.admin_delete_sgf, name='delete_sgf'),
    url(r'^division/(?P<pk>[0-9]+)/informations/$',
        views.DivisionUpdate.as_view(), name='division_update_infos'),
    url(r'^division/(?P<division_id>[0-9]+)/forfeit/create$',
        views.division_create_forfeit, name='division_create_forfeit'),
    url(r'^division/(?P<division_id>[0-9]+)/wont-play/$',
        views.division_update_wont_play, name='division_update_wont_play'),
    url(r'^division/(?P<division_id>[0-9]+)/wont-play/create$',
        views.division_create_wont_play, name='division_create_wont_play'),
    url(r'^division/(?P<division_id>[0-9]+)/wont-play/remove$',
        views.division_remove_wont_play, name='division_remove_wont_play'),
    url(r'^admin/events/(?P<event_id>[0-9]+)/create-division/$',
        views.admin_create_division, name='admin_create_division'),
    url(r'^admin/division/(?P<division_id>[0-9]+)/delete-division/$',
        views.admin_delete_division, name='admin_delete_division'),
    url(r'^admin/division/(?P<division_id>[0-9]+)/rename/$',
        views.admin_rename_division, name='admin_rename_division'),
    url(r'^admin/division/(?P<division_id>[0-9]+)/winner/$',
        views.division_set_winner, name='division_set_winner'),
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
    url(r'^scrap-list/(?P<profile_id>[0-9]+)/up/$',
        views.scrap_list_up, name='scrap_list_up'),
    url(r'^game/json/(?P<sgf_id>[0-9]+)/$', views.game_api, name='game_api'),
    url(r'^game/json/(?P<sgf_id>[0-9]+)/(?P<event_id>[0-9]+)/$',
        views.game_api, name='game_api'),

    url(r'^(?P<event_id>[0-9]+)/join/(?P<user_id>[0-9]+)/$',
        views.join_event, name='join_event'),
    url(r'^(?P<event_id>[0-9]+)/quit/$',
        views.quit_league, name='quit_league'),
    url(r'^(?P<event_id>[0-9]+)/quit/(?P<user_id>[0-9]+)/$',
        views.quit_league, name='quit_league'),

    url(r'^admin/create-profile/(?P<user_id>[0-9]+)$',
        views.create_profile, name='create_profile'),
    url(r'^admin/update-all-sgf-check-code/$',
        views.update_all_sgf_check_code, name='update_all_sgf_check_code'),
    url(
        r'^admin/update_all_profiles/$',
        views.update_all_profiles,
        name='update_all_profiles'
    ),
    url(r'^admin/set-meijin/$', views.admin_set_meijin, name='set_meijin'),
    url(r'^admin/download-ffg-tou/(?P<league_id>[0-9]+)/$',
        views.download_ffg_tou, name='download_ffg_tou'),
    url(
        r'^profile/update/$',
        views.ProfileUpdate.as_view(),
        name='profile_update'
    ),
    url(
        r'^profile/(?P<pk>[0-9]+)/update/$',
        views.ProfileUpdate.as_view(),
        name='profile_update'
    ),
    url(r'discord-api/$', views.discord_api, name='discord_api'),
    url(r'games-api/$', views.games_datatable_api, name='games_api'),
    url(r'user-leagues-manage/(?P<user_id>[0-9]+)/$',
        views.user_leagues_manage, name='user_leagues_manage'),
    url(r'random-game/$', views.random_game, name='random_game'),
]
