# -*- coding: utf-8 -*-

import os
from django.core.cache import caches
from django.views.generic import TemplateView


class AuthMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response
        self.pid = os.getpid()
        self.cache = caches['auth_user']
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        if request.user:
            self.cache.get_or_set(self.pid, request.user)
        response = self.get_response(request)
        self.cache.delete(self.pid)

        # Code to be executed for each request/response after
        # the view is called.

        return response

def get_auth_user():
    return caches['auth_user'].get(os.getpid(), None)


class MessagingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def process_template_response(self, request, response):
        if hasattr(response, 'context_data') and response.context_data:
            for x, y in response.context_data.items():
                print('{0}\t\t\t{1}'.format(x, y))
                print('#'*60)
        # response.context_data['context_menu'] = 'aFEFEFERGHR%E TGRE RE GSDFSD'
        return response

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        response = self.get_response(request)
        # Code to be executed for each request/response after
        # the view is called.

        return response
