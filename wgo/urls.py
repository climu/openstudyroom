from django.conf.urls import url

from . import views

app_name = 'wgo'


urlpatterns = [
    url(
        r'^tsumego-api/$',
        views.tsumego_api,
        name='tsumego_api'
    ),
]
