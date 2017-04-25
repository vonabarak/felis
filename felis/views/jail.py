# -*- coding: utf-8 -*-

from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView
from felis.models import Jail
from felis.models.rctl import rctls

__all__ = ['JailDetailView', 'JailListView']

class JailDetailView(DetailView):
    model = Jail
    template_name = 'detailed/jail.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        status = request.GET.get('status', None)
        console = request.GET.get('console', None)

        if status in ['r', 'start', 'on', '1']:
            self.object.status = Jail.STARTING
        elif status in ['s', 'stop', 'off', '0']:
            self.object.status = Jail.STOPPING
        if console in ['yes', 'on', 'true', '1']:
            self.object.console = True
        elif console in ['no', 'off', 'false', '0']:
            self.object.console = False
        if status or console:
            self.object.save()
            return HttpResponseRedirect(reverse_lazy('jail', kwargs={'pk': self.object.pk}))

        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super(JailDetailView, self).get_context_data(**kwargs)
        context['ssh'] = 'ssh felis@'+self.request.get_host()+' -p'+str(50000+self.object.id)
        context['charts'] = [i[0] for i in rctls]
        return context


class JailListView(ListView):
    template_name = 'listviews/jails.html'
    model = Jail

