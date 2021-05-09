import mistune

class osr_renderer(mistune.Renderer):
    def autolink(self, link, is_email=False):
        """ All point here is to disable autolink feature."""
        return link

    def image(self, src, title, text):
        """Rendering a image with title and text.
        :param src: source link of the image.
        :param title: title text of the image.
        :param text: alt text of the image.
        """
        src = mistune.escape_link(src)
        text = mistune.escape(text, quote=True)
        if title:
            title = mistune.escape(title, quote=True)
            html = '<img src="%s"  class="img-responsive" alt="%s" title="%s"' % (src, text, title)
        else:
            html = '<img src="%s" class="img-responsive" alt="%s"' % (src, text)
        return '%s />' % html



def osr_markdown(string, *args, **kwargs):
    renderer = osr_renderer()
    markdown = mistune.Markdown(renderer=renderer)
    return markdown(mistune.escape(string))
