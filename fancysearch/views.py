import json
from django.http import HttpResponse
from django.urls import reverse
from league.models import User
from home.models import FullWidthPage
from wagtail.search.backends import get_search_backend
from puput.models import BlogPage
from machina.core.db.models import get_model
from machina.core.loading import get_class


Forum = get_model('forum', 'Forum')
Topic = get_model('forum_conversation', 'Topic')

PermissionHandler = get_class('forum_permission.handler', 'PermissionHandler')


def users_search(request):
    query = request.GET.get('query', None)
    if query is not None:
        users = User.objects.filter(username__icontains=query).select_related('profile').prefetch_related('discord_user')[:5]
        results = []
        for user in users:
            user_dict = {'id': user.pk, 'username': user.username}
            if user.profile.kgs_username:
                user_dict.update({
                    'kgs_online': user.is_online_kgs(),
                    'kgs_username': user.profile.kgs_username,
                    'kgs_rank': user.profile.kgs_rank,
                })
            if user.profile.ogs_username:
                user_dict.update({
                    'ogs_online': user.is_online_ogs(),
                    'ogs_username': user.profile.ogs_username,
                    'ogs_rank': user.profile.ogs_rank,
                    'ogs_id': user.profile.ogs_id
                })

            discord_user = user.discord_user.first()
            if discord_user is not None:
                user_dict.update({
                    'discord_status': discord_user.status,
                    'discord_username': discord_user.username,
                    'discord_discriminator': discord_user.discriminator
                })

            results.append(user_dict)
        data = json.dumps(results)
    else:
        data = 'fail'
    mimetype = 'application/json'
    return HttpResponse(data, mimetype)


def pages_search(request):
    query = request.GET.get('query', None)
    s = get_search_backend()
    pages = s.search(query, FullWidthPage.objects.all())[:5]
    if query is not None:
        results = []
        for page in pages:
            results.append({
                'title': str(page),
                'url': page.get_url(request)
            })
        data = json.dumps(results)
    else:
        data = 'fail'
    mimetype = 'application/json'
    return HttpResponse(data, mimetype)


def blog_search(request):
    query = request.GET.get('query', None)
    if query is not None:
        blog_page = BlogPage.objects.first()
        entries = blog_page.get_entries().search(query)[:5]
        results = []
        for entry in entries:
            results.append({
                'title': entry.title,
                'url': entry.get_url(request)
            })
        data = json.dumps(results)
    else:
        data = 'fail'
    mimetype = 'application/json'
    return HttpResponse(data, mimetype)


def forum_search(request):
    query = request.GET.get('query', None)
    if query is not None:
        allowed_forums = PermissionHandler().get_readable_forums(Forum.objects.all(), request.user)
        topics = Topic.objects.filter(forum__in=allowed_forums, subject__icontains=query)[:5]
        results = []
        for topic in topics:
            url = reverse('forum_conversation:topic', kwargs={
                'forum_slug': topic.forum.slug,
                'forum_pk': topic.forum.pk,
                'slug': topic.slug,
                'pk': topic.id
            })
            results.append({
                'title': topic.subject,
                'url': url
            })
        data = json.dumps(results)
    else:
        data = 'fail'
    mimetype = 'application/json'
    return HttpResponse(data, mimetype)
