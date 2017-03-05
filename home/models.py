from __future__ import absolute_import, unicode_literals

from django.db import models
from django import forms
from wagtail.wagtailcore.models import Page, Orderable
from wagtail.wagtailcore.fields import RichTextField, StreamField
from wagtail.wagtailadmin.edit_handlers import FieldPanel, FieldRowPanel, MultiFieldPanel, \
    InlinePanel, PageChooserPanel, StreamFieldPanel
from wagtail.wagtailimages.edit_handlers import ImageChooserPanel
from wagtail.wagtaildocs.edit_handlers import DocumentChooserPanel
from wagtail.wagtailsnippets.models import register_snippet
from wagtail.wagtailforms.models import AbstractEmailForm, AbstractFormField
from wagtail.wagtailsearch import index

from wagtail.wagtailcore.blocks import TextBlock, StructBlock, StreamBlock, FieldBlock, CharBlock, RichTextBlock, RawHTMLBlock, IntegerBlock
from wagtail.wagtailimages.blocks import ImageChooserBlock
from wagtail.wagtaildocs.blocks import DocumentChooserBlock
from puput.models import EntryPage, BlogPage
from wagtailmenus.models import MenuPage


from machina.core.db.models import get_model
from machina.core.loading import get_class
import requests
import json


Forum = get_model('forum', 'Forum')
Topic = get_model('forum_conversation', 'Topic')

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
        ('normal', 'Normal'), ('right', 'Right'),('left','Left'),
    ))


class ImageBlock(StructBlock):
    image = ImageChooserBlock()
    caption = RichTextBlock()
    alignment = ImageFormatChoiceBlock()


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


class HomePage(Page):
     def get_context(self, request, *args, **kwargs):
         entries = EntryPage.objects.live().order_by('-date')
         blog_page = BlogPage.objects.all().first()
         allowed_forums = request.forum_permission_handler._get_forums_for_user(request.user,[ 'can_read_forum',])
         last_topics = Topic.objects.filter(forum__in = allowed_forums).order_by('-last_post_on')[:5]
         r = requests.get('https://discordapp.com/api/guilds/287487891003932672/widget.json')
         disc_users = r.json()['members']
         context = super(HomePage, self).get_context(request, *args, **kwargs)
         context['entries'] = entries
         context['blog_page'] = blog_page
         context['topics'] = last_topics
         context['disc_users'] = disc_users

         return context



class FullWidthPage(MenuPage):
    body = StreamField(MyStreamBlock(),blank=True)

    content_panels = Page.content_panels + [
        StreamFieldPanel('body'),
    ]

class RightSidebarPage(MenuPage):
    body = StreamField(MyStreamBlock(),blank=True)

    content_panels = Page.content_panels + [

        StreamFieldPanel('body'),
    ]

class LeftSidebarPage(MenuPage):
    body = StreamField(MyStreamBlock(),blank=True)

    content_panels = Page.content_panels + [

        StreamFieldPanel('body'),
    ]

class StreamFieldEntryPage(EntryPage):
    streamfield = StreamField(MyStreamBlock(),blank=True)
    content_panels = EntryPage.content_panels + [
        StreamFieldPanel('streamfield')
    ]
BlogPage.subpage_types.append(StreamFieldEntryPage)
