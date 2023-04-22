from django import template

register = template.Library()

@register.filter()
def datatable_tag(config):
    t = template.loader.get_template('home/tags/datatable.html')

    result = t.render(config)
    return result

  # return render(request, 'lld/lld_sections.html',{'document': document})
  # return mark_safe(html)
