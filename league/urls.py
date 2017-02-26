from django.conf.urls import url

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
    url(r'^(?P<event_id>[0-9]+)/games/$', views.games, name='games'),

    url(r'^players/$', views.players, name='players'),
    url(r'^(?P<event_id>[0-9]+)/players/$', views.players, name='players'),


    url(r'^account/$', views.account, name='league_account'),
    url(r'^account/(?P<user_name>[\w.@+-]+)/$', views.account,name='league_account'),
    url(r'^scraper/$', views.scraper, name='scraper'),

    url(r'^admin/$', views.admin, name='admin'),
    url(r'^sgf/(?P<sgf_id>[0-9]+)/$', views.sgf_view, name='sgf_edit'),
]
