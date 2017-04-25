# -*- coding: utf-8 -*-

from django.apps import AppConfig

default_app_config = 'felis.FelisAppConfig'


class FelisAppConfig(AppConfig):

    name = 'felis'

    def ready(self):
        # cannot be loaded before application is ready
        import felis.signals
