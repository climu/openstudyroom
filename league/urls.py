from django.conf.urls import url
from django.core.urlresolvers import reverse

from . import views

urlpatterns = [
    url(r'^$', views.event, name='event'),
    url(r'^results/$', views.results, name='results'),
    url(r'^rollover/$', views.rollover, name='rollover'),
    url(r'^proceed-rollover/$', views.proceed_rollover, name='proceed_rollover'),
    url(r'^archives/$', views.archives, name='archives'),

    url(r'^(?P<event_id>[0-9]+)/results/(?P<division_id>[0-9]+)/$',views.results,name='results'),
    url(r'^(?P<event_id>[0-9]+)/results/$',views.results,name='results'),

    url(r'^(?P<event_id>[0-9]+)/$',views.event,name='event'),

    url(r'^games/$', views.games, name='games'),
    url(r'^games/(?P<game_id>[0-9]+)/$', views.games, name='game'),
    url(r'^(?P<event_id>[0-9]+)/games/$', views.games, name='games'),
    url(r'^(?P<event_id>[0-9]+)/games/(?P<game_id>[0-9]+)/$', views.games, name='game'),

    url(r'^players/$', views.players, name='players'),
    url(r'^(?P<event_id>[0-9]+)/players/$', views.players, name='players'),

    url(r'^discord/$', views.discord_redirect, name='discord_redirect'),

    url(r'^sgf/(?P<sgf_id>[0-9]+)/$', views.sgf, name='sgf'),

    url(r'^account/$', views.account, name='league_account'),
    url(r'^account/(?P<user_name>[\w.@+-]+)/$', views.account,name='league_account'),
    url(r'^scraper/$', views.scraper_view, name='scraper'),

    url(r'^admin/$', views.admin, name='admin'),
    url(r'^admin/sgf/(?P<sgf_id>[0-9]+)/$', views.admin_edit_sgf, name='edit_sgf'),
    url(r'^admin/handle-upload-sgf/$', views.handle_upload_sgf, name='handle_upload_sgf'),
    url(r'^admin/upload-sgf/$', views.upload_sgf, name='upload_sgf'),
    url(r'^admin/create-sgf/$', views.create_sgf, name='create_sgf'),
    url(r'^admin/send-mail/$', views.send_user_mail, name='send_email'),
    url(r'^admin/update-all-sgf/$', views.update_all_sgf, name='update_all_sgf'),
    url(r'^admin/events/$', views.admin_events, name='admin_events'),
    url(r'^admin/events/(?P<pk>[0-9]+)/$', views.LeagueEventUpdate.as_view(success_url='/league/admin/events/'), name='admin_events_update' ),
    url(r'^admin/events/(?P<event_id>[0-9]+)/set_primary/$', views.admin_events_set_primary, name='set_primary'),
    url(r'^admin/sgf/$', views.admin_sgf_list, name='admin_sgf'),
    url(r'^admin/game/(?P<game_id>[0-9]+)/delete/$', views.admin_delete_game, name='delete_game'),
    url(r'^admin/events/(?P<event_id>[0-9]+)/create-division/$', views.admin_create_division, name='admin_create_division' ),

]
