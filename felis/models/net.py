# -*- coding: utf-8 -*-

import logging
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from .transaction import Model
from .jail import *

logger = logging.getLogger('felis.models')

class Interface(Model):
    """
    Represents network interface that can be used by jail
    """
    class Meta:
        verbose_name = 'Network interface'

    UNKNOWN = 0
    BRIDGE = 1
    LOOPBACK = 2

    name = models.CharField(max_length=64, blank=False, null=False, unique=True)
    type = models.SmallIntegerField(choices=(
        (UNKNOWN, 'unknown'),
        (BRIDGE, 'bridge'),
        (LOOPBACK, 'loopback'),
    ))
    description = models.TextField(blank=True, null=True)
    os_managed = models.BooleanField(
        default=True,
        help_text=_('Assume interface exists and managed by operating system')
    )

    def clean_fields(self, *args, **kwargs):
        import re
        if self.type == self.BRIDGE and not re.match(r'bridge\d+', self.name):
            raise ValidationError({'name': [_("Bridge interface name must be `bridge' following by a number"), ]})
        elif self.type == self.LOOPBACK and not re.match(r'lo\d+', self.name):
            raise ValidationError({'name': [_("Loopback interface name must be `lo' following by a number"), ]})
        super(Interface, self).clean_fields(*args, **kwargs)


    def task_create(self, t):
        if self.os_managed:
            return
        if self.type == self.BRIDGE:
            return t.exec('ifconfig {name} create')
        if self.type == self.LOOPBACK:
            return t.exec('ifconfig {name} create')

    task_delete = None

    @models.permalink
    def get_absolute_url(self):
        return 'interface', (), {'pk': self.pk}

    def __str__(self):
        return self.name


class IPAddress(models.Model):
    """
    Stores IP address (v6 or v4) netmask and :model:`felis.Interface` for using by jail
    """
    class Meta:
        verbose_name = 'IP address'
        verbose_name_plural = 'IP addresses'
        unique_together = (('jail', 'address'), ('interface', 'address'))

    jail = models.ForeignKey(Jail, related_name='addresses', null=True)
    interface = models.ForeignKey(Interface, related_name='addresses')
    address = models.GenericIPAddressField(protocol='both', unpack_ipv4=True, unique=True)
    netmask = models.PositiveSmallIntegerField()

    @property
    def protocol(self):
        if ':' in self.address:
            return 6
        else:
            return 4


    @models.permalink
    def get_absolute_url(self):
        return 'ipaddress', (), {'pk': self.pk}

    def __str__(self):
        return self.address
