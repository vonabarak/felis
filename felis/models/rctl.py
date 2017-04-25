# -*- coding: utf-8 -*-

from functools import reduce
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.db import models
from .transaction import Model
from felis.errors import *

__all__ = ['RctlMixin', 'RctlRule']

rctls = [
    # rctl(8) resource   rctl(8) possible action for resource

    ('cputime', ('log', 'devctl', 'sigkill', 'sigterm')),
    ('datasize', ('deny', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('stacksize', ('deny', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('coredumpsize', ('deny', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('memoryuse', ('deny', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('memorylocked', ('deny', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('maxproc', ('deny', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('openfiles', ('deny', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('vmemoryuse', ('deny', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('pseudoterminals', ('deny', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('swapuse', ('deny', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('nthr', ('deny', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('msgqqueued', ('deny', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('msgqsize', ('deny', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('nmsgq', ('deny', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('nsem', ('deny', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('nsemop', ('deny', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('nshm', ('deny', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('shmsize', ('deny', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('wallclock', ('log', 'devctl', 'sigkill', 'sigterm')),
    ('pcpu', ('deny', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('readbps', ('throttle', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('writebps', ('throttle', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('readiops', ('throttle', 'log', 'devctl', 'sigkill', 'sigterm')),
    ('writeiops', ('throttle', 'log', 'devctl', 'sigkill', 'sigterm')),
]


def make_action_choices():
    """
    :return: choices list for django's CharField
    """
    # sorted need here to avoid db migration every time choices order randoms
    return [(i, i) for i in sorted(reduce(lambda x, y: x|y,  [set(rctl[1]) for rctl in rctls], set()))]

def make_resource_choices():
    """
    :return: choices list for django's model.CharField
    """
    return [(i[0], i[0]) for i in rctls]

def make_task_method(rctl):
    rctl_field = 'rctl_' + rctl[0]
    rctl_action_field = 'rctl_' + rctl[0] + '_action'
    cmd_exec_string = 'rctl -a jail:{{name}}:{0}:{{{1}}}={{{2}}}'.format(rctl[0], rctl_action_field, rctl_field)

    def task_method(_self, t):
        t.exec(cmd_exec_string)

    return task_method

def _rctl_mixin_model_generator():
    """
    A function to dynamicaly generate class-predcessor to inherit by :model:`felis.Jail` class
    :return: :model:`felis.RtclMixin` class
    """

    class Meta:
        abstract = True

    attrs = {'__module__': __name__, 'Meta': Meta}
    for rctl in rctls:
        attrs['rctl_'+rctl[0]] = models.IntegerField(null=True, blank=True, editable=False)


    return type('RctlMixin', (models.Model, ), attrs)

RctlMixin = _rctl_mixin_model_generator()

def update_current_rctls():
    from .jail import Jail
    from felis.utils import run_shell_command
    for jail in Jail.objects.filter(status=Jail.RUNNING):
        errcode, stdout, stderr = run_shell_command("rctl -u jail:{0}".format(jail.name))
        if errcode != 0:
            raise RctlUpdateFailed()
        for line in stdout.split(b'\n'):
            if line.strip():
                resource, amount = line.split(b'=')
                setattr(jail, 'rctl_'+resource.decode('utf-8'), int(amount))
        jail.save()


class RctlRule(Model):

    class Meta:
        verbose_name = 'rctl rule'
        # unique_together = (('jail', 'resource', 'action', 'per'),)
        # index_together = (('jail', 'resource', 'action', 'per'),)

    jail = models.ForeignKey('felis.Jail', related_name='rctl_rules', db_index=True)
    resource = models.CharField(max_length=16, choices=make_resource_choices())
    action = models.CharField(max_length=16, choices=make_action_choices())
    amount = models.BigIntegerField()
    per = models.CharField(max_length=16, null=True, blank=True)

    def clean_fields(self, exclude=None):
        for rctl in rctls:
            if (self.resource == rctl[0]) and (self.action not in rctl[1]):
                raise ValidationError({
                    'action':_(
                        "Action `{0}' is not allowed for rctl resource `{1}'").format(self.action, self.resource),
                    'resource': _(
                        "Action `{0}' is not allowed for rctl resource `{1}'").format(self.action, self.resource),
                })
        super(RctlRule, self).clean_fields(exclude=exclude)

    def task_create(self, t):
        if self.per:
            per = '/{per}'
        else:
            per = ''
        t.exec('rctl -a jail:{jail.name}:{resource}:{action}={amount}'+per)

    def task_delete(self, t):
        t.exec('rctl -r jail:{jail_name}:{resource}:{action}'.format(
            jail_name=t.old_instance.jail.name,
            resource=t.old_instance.resource,
            action=t.old_instance.action
        ))

    def task_update_jail(self, t):
        try:
            self.task_delete(t)
        except TaskFailed:
            pass
        self.task_create(t)
    task_update_resource = task_update_jail
    task_update_action = task_update_jail
    task_update_amount = task_update_jail
    task_update_per = task_update_jail

    def __str__(self):
        return 'rule #{0} {1}:{2}:{3}={4}'.format(self.id, self.jail.name, self.resource, self.action, self.amount)
