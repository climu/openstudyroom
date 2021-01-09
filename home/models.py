from __future__ import absolute_import, unicode_literals
import random

import requests
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.db.models import Count, Case, IntegerField, When
from django.db.models.functions import TruncMonth
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.encoding import python_2_unicode_compatible
from django.utils import timezone
from django import forms
from django.urls import reverse
from wagtail.core.models import Page
from wagtail.core.fields import RichTextField, StreamField
from wagtail.snippets.models import register_snippet
from wagtail.snippets.blocks import SnippetChooserBlock
from wagtail.admin.edit_handlers import FieldPanel, StreamFieldPanel
from wagtail.core.blocks import TextBlock, StructBlock, StreamBlock, FieldBlock, CharBlock, \
    RichTextBlock, RawHTMLBlock, IntegerBlock
from wagtail.images.blocks import ImageChooserBlock
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.contrib.table_block.blocks import TableBlock
from wagtail.core.signals import page_published
from wagtailmenus.models import MenuPage
from puput.models import EntryPage, BlogPage
from machina.core.db.models import get_model
from machina.apps.forum_conversation.forum_polls.models import TopicPoll
from league.models import Registry, Sgf, LeagueEvent


ForumPost = get_model('forum_conversation', 'Post')
TopicPoll.__module__ = "machina.apps.forum_conversation.forum_polls.models"

register_snippet(TopicPoll)

@register_snippet
@python_2_unicode_compatible  # provide equivalent __unicode__ and __str__ methods on Python 2
class Advert(models.Model):
    title = models.CharField(max_length=255)
    url = models.URLField(null=True, blank=True)
    body = RichTextField(blank=True)

    panels = [
        FieldPanel('title'),
        FieldPanel('url'),
        FieldPanel('body', classname="full"),
    ]

    def __str__(self):
        return self.title


@register_snippet
@python_2_unicode_compatible  # provide equivalent __unicode__ and __str__ methods on Python 2
class Quote(models.Model):
    text = models.TextField(blank=True, null=True, max_length=100)
    source = models.TextField(blank=True, null=True, max_length=20)
    panels = [
        FieldPanel('text'),
        FieldPanel('source'),
    ]

    def __str__(self):
        return self.text[0:30]

# Global Streamfield definition


class PullQuoteBlock(StructBlock):
    quote = TextBlock("quote title")
    attribution = CharBlock()

    class Meta:
        icon = "openquote"


class ImageFormatChoiceBlock(FieldBlock):
    field = forms.ChoiceField(choices=(
        ('left', 'Wrap left'), ('right', 'Wrap right'), ('mid', 'Mid width'), ('full', 'Full width'),
    ))


class HTMLAlignmentChoiceBlock(FieldBlock):
    field = forms.ChoiceField(choices=(
        ('normal', 'Normal'), ('full', 'Full width'),
    ))

class WgoAlignmentChoiceBlock(FieldBlock):
    field = forms.ChoiceField(choices=(
        ('normal', 'Normal'), ('right', 'Right'), ('left', 'Left'),
    ))


class ImageBlock(StructBlock):
    image = ImageChooserBlock()
    caption = RichTextBlock(blank=True, null=True, required=False)
    alignment = ImageFormatChoiceBlock()
    width = IntegerBlock(
        default=None,
        blank=True,
        null=True,
        required=False,
        help_text="optional width in px. Default is auto."
    )


class AlignedHTMLBlock(StructBlock):
    html = RawHTMLBlock()
    alignment = HTMLAlignmentChoiceBlock()

    class Meta:
        icon = "code"

class WgoBlock(StructBlock):
    sgf = DocumentChooserBlock()
    alignment = WgoAlignmentChoiceBlock()
    width = IntegerBlock(default=700)
    class Meta:
        icon = "placeholder"
        template = "wgo/wgoblock.html"


class MyStreamBlock(StreamBlock):
    h2 = CharBlock(icon="title", classname="title")
    h3 = CharBlock(icon="title", classname="title")
    h4 = CharBlock(icon="title", classname="title")
    intro = RichTextBlock(icon="pilcrow")
    paragraph = RichTextBlock(icon="pilcrow")
    aligned_image = ImageBlock(label="Aligned image", icon="image")
    pullquote = PullQuoteBlock()
    aligned_html = AlignedHTMLBlock(icon="code", label='Raw HTML')
    document = DocumentChooserBlock(icon="doc-full-inverse")
    wgo = WgoBlock(label="wgo")
    table = TableBlock()
    poll = SnippetChooserBlock(TopicPoll, template="home/includes/poll.html")


class HomePage(Page):
    def get_context(self, request, *args, **kwargs):
        entries = EntryPage.objects.live().order_by('-date')[0:3]
        blog_page = BlogPage.objects.all().first()
        context = super(HomePage, self).get_context(request, *args, **kwargs)
        context['entries'] = entries
        context['blog_page'] = blog_page
        quotes = Quote.objects.all()
        if quotes:
            quote = random.choice(Quote.objects.all())
            context['quote'] = quote
        context['discord_presence_count'] = Registry.get_discord_presence_count()
        first_of_the_month = timezone.now().date().replace(day=1)
        games = Sgf.objects\
            .exclude(date__isnull=True)\
            .defer('sgf_text')\
            .filter(league_valid=True)\
            .filter(date__gte=first_of_the_month)\
            .annotate(month=TruncMonth('date'))\
            .values('month')\
            .annotate(total=Count('id'))\
            .annotate(kgs=Count(
                Case(
                    When(place__startswith="The KGS", then=1),
                    output_field=IntegerField(),
                    distinct=True
                )))\
            .annotate(ogs=Count(
                Case(
                    When(place__startswith="OGS", then=1),
                    output_field=IntegerField(),
                    distinct=True
                )))\
            .values('total', 'kgs', 'ogs')
        if games:
            context['games'] = games[0]
        else:
            context['games'] = {"total":0}
        n_leagues = LeagueEvent.objects.filter(is_open=True, is_public=True, community__isnull=True).count()
        context['n_leagues'] = n_leagues
#        user = request.user
#        if user.is_authenticated and user.is_league_member:
#            now = timezone.now()
#            opponents = user.get_opponents()
#            if opponents is False:
#                context['should_join'] = True
#            else:
#                availables = AvailableEvent.objects.filter(
#                    end__gte=now,
#                    user__in=opponents
#                ).order_by('start')[:5]
#                context['availables'] = availables
#                online_opponents = list(filter(
#                    lambda user: user.is_online(),
#                    opponents
#                ))
#                context['online_opponents'] = online_opponents
#                game_requests = GameRequestEvent.objects.filter(
#                    receivers=user,
#                    end__gte=now
#                ).count()
#                context['game_requests'] = game_requests
#            me_available = AvailableEvent.objects.filter(
#                user=user,
#                end__gte=now
#            ).exists()
#            context['me_available'] = me_available
        return context


class FullWidthPage(MenuPage):
    body = StreamField(MyStreamBlock(), blank=True)

    content_panels = Page.content_panels + [
        StreamFieldPanel('body'),
    ]

class RightSidebarPage(MenuPage):
    body = StreamField(MyStreamBlock(), blank=True)

    content_panels = Page.content_panels + [

        StreamFieldPanel('body'),
    ]

class LeftSidebarPage(MenuPage):
    body = StreamField(MyStreamBlock(), blank=True)

    content_panels = Page.content_panels + [

        StreamFieldPanel('body'),
    ]

class StreamFieldEntryPage(EntryPage):
    streamfield = StreamField(MyStreamBlock(), blank=True)
    content_panels = EntryPage.content_panels + [
        StreamFieldPanel('streamfield')
    ]
BlogPage.subpage_types.append(StreamFieldEntryPage)


# Let everyone know when a new page is published
def send_to_discord(sender, **kwargs):
    instance = kwargs['instance']
    # Only post new post. No updates.
    if instance.first_published_at != instance.last_published_at:
        return

    if settings.DEBUG:
        return
    else:
        with open('/etc/discord_hook_url.txt') as f:
            discord_url = f.read().strip()

    excerpt = render_to_string(
        'home/includes/excerpt.html',
        {'entry': instance}
    )
    # I tryed to convert excerpt to markdown using tomd without success
    values = {
        "content": "Breaking news on OSR website !",
        "embeds": [{
            "title": instance.title,
            "url": "https://openstudyroom.org" + instance.url,
            "description": excerpt,
        }]
    }
    r = requests.post(discord_url, json=values)
    r.raise_for_status()


# Register two receivers
page_published.connect(send_to_discord, sender=EntryPage)
page_published.connect(send_to_discord, sender=StreamFieldEntryPage)


@receiver(post_save, sender=ForumPost)
def forum_post_to_discord(sender, instance, **kwargs):
    # don't announce edits
    instance.refresh_from_db()
    if instance.updates_count > 0:
        return
    # don't announce private admins forums forum.
    # This should be properly handled with a test if anonymous user can read forum.
    parent_id = instance.topic.forum.parent
    if parent_id is not None and parent_id.pk == 12:
        return
    if settings.DEBUG:
        return
    else:
        with open('/etc/discord_forum_hook_url.txt') as f:
            discord_url = f.read().strip()

    excerpt = render_to_string(
        'home/includes/forum_post_excerpt.html',
        {'content': instance.content}
    )
    # I tryed to convert excerpt to markdown using tomd without success
    url = reverse(
        'forum_conversation:topic',
        kwargs={
            'forum_slug': instance.topic.forum.slug,
            'forum_pk': instance.topic.forum.pk,
            'slug': instance.topic.slug,
            'pk': instance.topic.pk,
        }) + '?post=' + str(instance.pk) + '#' + str(instance.pk)

    values = {
        "content": 'from ' + instance.poster.username + ' in ' + instance.topic.forum.name,
        "embeds": [{
            "title": instance.subject,
            "url": 'https://openstudyroom.org' + url,
            "description": excerpt,
        }]
    }
    r = requests.post(discord_url, json=values)
    r.raise_for_status()
