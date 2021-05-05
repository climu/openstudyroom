from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.views.i18n import JavaScriptCatalog
from machina.app import board
from puput import urls as puput_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.core import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from search import views as search_views

urlpatterns = [
    url(r'^django-admin/', admin.site.urls),

    url(r'^admin/', include(wagtailadmin_urls)),
    url(r'^documents/', include(wagtaildocs_urls)),
    url(r'^comments/', include('django_comments_xtd.urls')),
    url(r'jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    url(r'^search-api/', include('fancysearch.urls', namespace="fancysearch")),

    url(r'^search/$', search_views.search, name='search'),

    url(r'^league/', include('league.urls', namespace="league")),
    url(r'^stats/', include('stats.urls', namespace="stats")),
    url(r'^wgo/', include('wgo.urls', namespace="wgo")),


#    url(r'^wgo/', include('wgo.urls', namespace="wgo")),
#    url(r'^accounts/login/$',LoginView.as_view(), name="auth_login"),
#    url(r'^accounts/signup/$',SignupView.as_view(), name="registration_register"),

    url(r'^calendar/', include('fullcalendar.urls', namespace='calendar')),

    url(r'^accounts/', include('allauth.urls')),
    url(r'^forum/', include(board.urls)),

    url(r'^tournament/', include('tournament.urls', namespace='tournament')),

    url(r'^discord/', include('discord_bind.urls')),

    url(r'^messages/', include('postman.urls', namespace='postman')),
    url(r'^community/', include('community.urls', namespace='community')),
    url(r'', include(puput_urls)),
    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's page serving mechanism. This should be the last pattern in
    # the list:
    url(r'', include(wagtail_urls)),

    # Alternatively, if you want Wagtail pages to be served from a subpath
    # of your site, rather than the site root:
    #    url(r'^pages/', include(wagtail_urls)),
]
if settings.DEBUG:
    # pylint: disable=ungrouped-imports
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
