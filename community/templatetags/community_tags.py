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
