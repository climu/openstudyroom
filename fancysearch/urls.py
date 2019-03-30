from django.conf.urls import url

from . import views

app_name = 'fullcalendar'


urlpatterns = [
    url(
        r'^users/',
        views.users_search,
        name='users_search'
    ),
    url(
            r'^pages/',
            views.pages_search,
            name='pages_search'
    ),
    url(
            r'^blog/',
            views.blog_search,
            name='blog_search'
    ),
    url(
            r'^forum/',
            views.forum_search,
            name='forum_search'
    ),
    ]
