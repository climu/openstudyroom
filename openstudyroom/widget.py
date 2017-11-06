from __future__ import unicode_literals

from django.forms.widgets import Textarea

class MarkdownTextareaWidget(Textarea):
    """ A simple Textarea widget using the simplemde JS library to provide Markdown editor. """
    class Media:
        css = {
            'all': ('mdeditor/bootstrap-markdown.min.css', ),
        }
        js = (
            'mdeditor/bootstrap-markdown.js',
            '//cdnjs.cloudflare.com/ajax/libs/marked/0.3.6/marked.min.js',
            '//cdnjs.cloudflare.com/ajax/libs/ace/1.2.9/ace.js'
        )

    def render(self, name, value, attrs=None, renderer=None):
        attrs = {} if attrs is None else attrs
        classes = attrs.get('classes', '')
        #attrs['id'] = "markdown-editor"
        attrs['data-provide'] = "markdown"
        attrs['data-height'] = "500"
        attrs['class'] = classes + ' machina-mde-markdown'
        return super(MarkdownTextareaWidget, self).render(name, value, attrs)
