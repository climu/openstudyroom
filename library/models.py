from django.db import models
from django.utils.text import slugify
from taggit.managers import TaggableManager
from machina.core import validators
from machina.core.db.models import get_model
from machina.models.fields import MarkupTextField
Topic = get_model('forum_conversation', 'Topic')


class Library_entry(models.Model):
    TYPE_CHOICES = (
        ('link', 'link'),
        ('video', 'video'),
        ('forum', 'forum'),
    )
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    title = models.CharField(max_length=20, unique=True)
    slug = models.SlugField()
    teacher = models.CharField(max_length=30, blank=True, null=True)
    teacher_url = models.URLField(blank=True, null=True)
    description = MarkupTextField(
            blank=True, null=True,
            validators=[validators.NullableMaxLengthValidator(2000)]
    )
    url = models.URLField(blank=True)
    tags = TaggableManager()

    def save(self, *args, **kwargs):
        if not self.id:
            # Newly created object, so set slug
            self.slug = slugify(self.title)
            # if url is None, populate from slug
            if not self.url:
                self.url = "/" + self.slug + "/"
        super(Library_entry, self).save(*args, **kwargs)


class Forum_entry(Library_entry):
    """ Special entry made from a forum post """
    forum_post = models.ForeignKey(Topic, on_delete=models.CASCADE)
