from django import template
from home.models import Advert
from machina.core.db.models import get_model
from machina.core.loading import get_class
import requests
import json


Forum = get_model('forum', 'Forum')
Topic = get_model('forum_conversation', 'Topic')
TopicPollVoteForm = get_class('forum_polls.forms', 'TopicPollVoteForm')
register = template.Library()

@register.inclusion_tag('home/tags/adverts.html', takes_context=True)
def adverts(context):
    return {
        'adverts': Advert.objects.all(),
        'request': context['request'],
    }

@register.simple_tag()
def last_topics(request):
    allowed_forums = request.forum_permission_handler._get_forums_for_user(request.user,[ 'can_read_forum',])
    last_topics = Topic.objects.filter(forum__in=allowed_forums).order_by('-last_post_on')[:4]
    return last_topics


@register.simple_tag()
def discord_users():
    r = requests.get('https://discordapp.com/api/guilds/287487891003932672/widget.json')
    disc_users = r.json()['members']
    return disc_users

@register.simple_tag()
def get_poll_form(poll):
    return TopicPollVoteForm(poll=poll)
