# -*- coding: utf-8 -*-

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

__all__ = ['PaginationMixin']

class PaginationMixin:

    def add_paginator(self, context):
        rows = 12
        page = 1
        paginator = Paginator(context.get('object_list', list()), rows)
        try:
            show_lines = paginator.page(self.request.GET.get('page', page))
        except PageNotAnInteger:
            show_lines = paginator.page(page)
        except EmptyPage:
            show_lines = paginator.page(paginator.num_pages)
        context['paginator'] = paginator
        context['object_list'] = show_lines
        context['rows'] = rows
        context['page'] = page
        return context
