import mistune

class osr_renderer(mistune.Renderer):
    def autolink(self, link, is_email=False):
        """ All point here is to disable autolink feature."""
        return link


def osr_markdown(string, *args, **kwargs):
    renderer = osr_renderer()
    markdown = mistune.Markdown(renderer=renderer)
    return markdown(string)
