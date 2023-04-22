from django import template
from django.template import Context, Template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter()
def datatable_tag(config):
    t = template.loader.get_template('home/tags/datatable.html')

    result = t.render(config)
    return result

  # return render(request, 'lld/lld_sections.html',{'document': document})
  # return mark_safe(html)
