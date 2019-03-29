import json
from django.http import HttpResponse

from league.models import User
from home.models import FullWidthPage
from wagtail.search.backends import get_search_backend

def users_search(request):
    query = request.GET.get('query', None)
    s = get_search_backend()
    pages = s.search(query, FullWidthPage.objects.all())
    if query is not None:
        users = User.objects.filter(username__icontains=query).select_related('profile').prefetch_related('discord_user')
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
    pages = s.search(query, FullWidthPage.objects.all())
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
