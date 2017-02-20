from django.conf.urls import url

from . import views

urlpatterns = [

    url(r'^game/(?P<game_id>[0-9]+)/$', views.wgo_game_view,name='game_iframe'),

]
