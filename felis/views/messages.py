# -*- coding: utf-8 -*-

from django.contrib.messages.api import MessageFailure, constants
from django.http import HttpRequest
from django.utils.html import mark_safe

def add_message(request, level, message, extra_tags='', fail_silently=False, buttons=None):
   """
   Attempts to add a message to the request using the 'messages' app.
   """
   if not isinstance(request, HttpRequest):
       raise TypeError("add_message() argument must be an HttpRequest object, "
                       "not '%s'." % request.__class__.__name__)
   if hasattr(request, '_messages'):
       if buttons:
           b = ''.join([
               '<td><a class="btn btn-{style}" href="{href}">{text}</a></td>'.format(
                   text=text, style=style, href=href)
               for text, style, href in buttons
           ])
       else:
           b = ''
       return request._messages.add(
           level, mark_safe((
               '<table style="width: 95%;">'
                   '<tr>'
                       '<td>{msg}</td>'
                       '<td></td>'
                       '{buttons}'
                   '</tr>'
               '</table>').format(msg=message, buttons=b)))
   if not fail_silently:
       raise MessageFailure(
           'You cannot add messages without installing '
           'django.contrib.messages.middleware.MessageMiddleware'
       )

def debug(request, message, extra_tags='', fail_silently=False, buttons=None):
    """
    Adds a message with the ``DEBUG`` level.
    """
    add_message(request, constants.DEBUG, message, extra_tags=extra_tags,
                fail_silently=fail_silently, buttons=buttons)


def info(request, message, extra_tags='', fail_silently=False, buttons=None):
    """
    Adds a message with the ``INFO`` level.
    """
    add_message(request, constants.INFO, message, extra_tags=extra_tags,
                fail_silently=fail_silently, buttons=buttons)


def success(request, message, extra_tags='', fail_silently=False, buttons=None):
    """
    Adds a message with the ``SUCCESS`` level.
    """
    add_message(request, constants.SUCCESS, message, extra_tags=extra_tags,
                fail_silently=fail_silently, buttons=buttons)


def warning(request, message, extra_tags='', fail_silently=False, buttons=None):
    """
    Adds a message with the ``WARNING`` level.
    """
    add_message(request, constants.WARNING, message, extra_tags=extra_tags,
                fail_silently=fail_silently, buttons=buttons)


def error(request, message, extra_tags='', fail_silently=False, buttons=None):
    """
    Adds a message with the ``ERROR`` level.
    """
    add_message(request, constants.ERROR, message, extra_tags=extra_tags,
                fail_silently=fail_silently, buttons=buttons)
