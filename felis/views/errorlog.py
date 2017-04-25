# -*- coding: utf-8 -*-

from django.views.generic import ListView
from .pagination import PaginationMixin
from selfcheck.models import StatusLog
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test

__all__ = ['ErrorLogView']

class ErrorLogView(ListView, PaginationMixin):
    model = StatusLog
    template_name = 'errorlog.html'

    @method_decorator(user_passes_test(lambda u: u.is_superuser))
    def dispatch(self, *args, **kwargs):
        return super(self.__class__, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        level = self.request.GET.get('level', '0')
        logger = self.request.GET.get('logger', None)
        if logger:
            return StatusLog.objects.filter(level__gte=level, logger_name=logger).order_by('-id')
        else:
            return StatusLog.objects.filter(level__gte=level).order_by('-id')

    def get_context_data(self, **kwargs):
        context = super(self.__class__, self).get_context_data(**kwargs)
        level = self.request.GET.get('level', '0')
        logger = self.request.GET.get('logger', '')
        context['level'] = level
        context['logger'] = logger
        return self.add_paginator(context)

