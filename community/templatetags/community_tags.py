from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter()
def community_link(community, slug=None):
    if community is None:
        return ''
    link = '<a href="'
    link += reverse(
        'community:community_page',
        kwargs={'slug': community.slug}
    )
    link += '">' + community.name + '</a>'
    return mark_safe(link)

@register.filter()
def new_member_communities(user):
    communities = user.groups.\
        filter(name__icontains='_community_new_member').\
        values_list('new_user_community__name', flat=True)
    return mark_safe(', '.join(communities))
