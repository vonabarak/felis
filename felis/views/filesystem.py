# -*- coding: utf-8 -*-

from django.views.generic import DetailView, ListView
from felis.models import Filesystem

__all__ = ['FilesystemListView', 'FilesystemDetailView']

class FilesystemListView(ListView):
    template_name = 'listviews/filesystems.html'
    model = Filesystem


class FilesystemDetailView(DetailView):
    model = Filesystem
    template_name = 'detailed/filesystem.html'
