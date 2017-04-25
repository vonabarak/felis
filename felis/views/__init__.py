# -*- coding: utf-8 -*-

import logging
from datetime import timedelta
from django.utils import timezone
from django.views.generic import \
    View, TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView, RedirectView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test, login_required

from django.db.models import Q
from django.urls import reverse_lazy, reverse
from felis.views import messages
from felis.models import *

from .charts import *
from .transactions import *
from .errorlog import *
from .jail import *
from .filesystem import *
from .api import *


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class HomePageView(TemplateView):
    template_name = 'home.html'


    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(self.__class__, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        print('PRINT FROM VIEW', request.COOKIES)
        return super(HomePageView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(self.__class__, self).get_context_data(**kwargs)
        if self.request.user:
            context['problems'] = Transaction.objects.filter(
                Q(rolledback__gt=timezone.now()-timedelta(days=1)) &
                Q(author=self.request.user)
            )
        for i in context['problems']:
            msg = '{0} failed'.format(i)
            messages.info(self.request, msg, buttons=[('OK', 'danger', 'http://ya.ru')])
        if self.request.user and not self.request.user.preferences.ssh_pubkey:
            messages.info(self.request, 'Please define your ssh public key in preferences',
                             buttons=[('OK', 'primary', reverse('admin:felis_userpreferences_change', args=(self.request.user.pk, ))), ])
        return context


class WorldListView(ListView):
    template_name = 'listviews/filesystems.html'
    model = World


class SkelListView(ListView):
    template_name = 'listviews/filesystems.html'
    model = Skel


class WorldDetailView(DetailView):
    model = World
    template_name = 'detailed/world.html'


class SkelDetailView(DetailView):
    model = Skel
    template_name = 'detailed/skel.html'


class InterfaceListView(ListView):
    model = Interface
    template_name = 'listviews/interfaces.html'


class InterfaceDetailView(DetailView):
        model = Interface
        template_name = 'detailed/interface.html'


class IPAddressListView(ListView):
    model = IPAddress
    template_name = 'listviews/ipaddresses.html'


class IPAddressDetailView(DetailView):
        model = IPAddress
        template_name = 'detailed/ipaddress.html'



