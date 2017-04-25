# -*- coding: utf-8 -*-

from django.db import models
from django.conf import settings

__all__ = ['UserPreferences']

class UserPreferences(models.Model):
    """
    Model to store authenticated user's prefrenses and settings
    """

    class Meta:
        verbose_name = 'User preferences'
        verbose_name_plural = 'Users preferences'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=False, primary_key=True, related_name='preferences', editable=False)
    ssh_pubkey = models.TextField(null=True, blank=True)

    def __str__(self):
        return 'Preferences for {0}'.format(self.user)

