# -*- coding: utf-8 -*-

from django.db.models import Q
from django.views.generic import ListView
from felis.models import Transaction
from .pagination import PaginationMixin

__all__ = ['TransactionListView']

class TransactionListView(ListView, PaginationMixin):
    model = Transaction
    template_name = 'listviews/transactions.html'

    def get_queryset(self):
        show_system = self.request.GET.get('show_system', None)
        if show_system:
            return self.model.objects.all()
        else:
            return self.model.objects.filter(~Q(author=None))

    def get_context_data(self, **kwargs):
        context_data = super(TransactionListView, self).get_context_data(**kwargs)
        context_data['show_system'] = self.request.GET.get('show_system', None)
        return self.add_paginator(context_data)
