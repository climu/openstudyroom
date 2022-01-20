from django import template
from django.utils.safestring import mark_safe
from django.template import Context, Template

register = template.Library()

@register.filter()
def datatable_tag(columns):
    t = template.loader.get_template('home/tags/datatable.html')
    context = {
      "columns": columns
    }

    result = t.render(context)
    return result

  # return render(request, 'lld/lld_sections.html',{'document': document})
  # return mark_safe(html)
