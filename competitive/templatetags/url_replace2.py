from django import template

register = template.Library()


@register.simple_tag
@register.filter(name='url_replace2')
def url_replace2(request, field, value, field2, value2):
    query_string = request.GET.copy()
    query_string[field] = value
    query_string[field2] = value2
    
    return query_string.urlencode()