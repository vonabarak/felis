# -*- coding: utf-8 -*-

from django import template
import re
register = template.Library()


@register.simple_tag
def active(request, pattern):
    if re.search(pattern, request.path):
        return 'bg-success'
    return ''


@register.filter
def get(dictionary, key):
    if dictionary.__class__ == dict:
        return dictionary.get(key)
    else:
        return None


@register.filter
def json_prettyfy(dic):
    import json
    return json.dumps(dic, indent=1)


@register.inclusion_tag('blocks/pagination.html')
def paginator(page, request, **kwargs):
    from bootstrap3.templatetags.bootstrap3 import get_pagination_context
    pagination_kwargs = kwargs.copy()
    pagination_kwargs['page'] = page
    if 'url' not in pagination_kwargs:
        pagination_kwargs['url'] = request.get_full_path()
    return get_pagination_context(**pagination_kwargs)
