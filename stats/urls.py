from django.conf.urls import url

from . import views


app_name = 'stats'

urlpatterns = [
    url(
        r'^$',
        views.overview,
        name='overview'
    ),
]
