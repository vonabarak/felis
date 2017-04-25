# -*- coding: utf-8 -*-

import logging
import django.db.models as models
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.contrib.postgres.fields import JSONField
from django.contrib.contenttypes.models import ContentType
from django.core.cache import caches
from django_q.models import Task
from polymorphic.models import PolymorphicModel
from felis.errors import *

__all__ = ['Transaction', 'Model']

logger = logging.getLogger('felis.models')

class Transaction(models.Model):
    """
    Represents a change or set of changes in a :model:`felis.Model`'s instance that may require executing some tasks.
    Also :model:`felis.Transaction`'s instances may be used as a historical marks for some :model:`felis.Model`'s fields.
    """

    class Meta:
        verbose_name = 'Transaction'
        ordering = ["-pk"]

    cache = caches['transaction']

    CREATE = 0
    UPDATE = 1
    DELETE = 2

    instance = models.ForeignKey(
        'Model', related_name='transactions', on_delete=models.SET_NULL,
        null=True, db_index=True, blank=True, editable=False)
    content_type = models.ForeignKey(ContentType, null=True, db_index=True, blank=True)

    change_type = models.PositiveSmallIntegerField(
        choices=((CREATE, 'CREATE'), (UPDATE, 'UPDATE'), (DELETE, 'DELETE')),
        db_index=True
    )

    created = models.DateTimeField(auto_now_add=True)
    started = models.DateTimeField(null=True, default=None, db_index=True, blank=True)
    committed = models.DateTimeField(null=True, default=None, db_index=True, blank=True)
    rolledback = models.DateTimeField(null=True, default=None, db_index=True, blank=True)
    value = JSONField(null=True, db_index=True, blank=True)
    task = models.OneToOneField(Task, related_name='transaction', null=True, db_index=True, blank=True, editable=False)
    depends = models.ManyToManyField('self', symmetrical=True, db_index=True, blank=True, editable=False)
    priority = models.PositiveSmallIntegerField(db_index=True, null=True, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, db_index=True, null=True, blank=True)

    def full_clean(self, *args, **kwargs):
        # transaction cannot be committed and rolledback simultaneously
        if self.committed and self.rolledback:
            msg = _("Transaction cannot be committed and rolled back simultaneously")
            raise ValidationError({'committed': [msg, ], 'rolledback': [msg, ]})

        # validating `change_type' field
        if (self.change_type == self.CREATE)\
                and self.value is None\
                and self.instance is not None:
            pass
        elif (self.change_type == self.UPDATE) \
                and self.value is not None\
                and self.instance is not None:
            pass
        elif (self.change_type == self.DELETE)\
                and self.value is not None\
                and self.instance is None:
            pass
        else:
            raise ValidationError({'change_type': [_(
                "Didnt expected data for change of type {0}").format(self.change_type), ]})

        # setting priority
        if self.priority is None:
            self.priority = self.get_priority()

        super(Transaction, self).full_clean(*args, **kwargs)

    @property
    def previous(self):
        return self.instance.transactions.filter(committed__lt=self.created).order_by('-committed').first()

    @property
    def next(self):
        return self.instance.transactions.filter(committed__gt=self.created).order_by('committed').first()

    @property
    def cached_data(self):
        return self.cache.get(self.pk, None)

    @property
    def old_values_dict(self):
        cached_values = self.cache.get(self.pk, dict())
        if cached_values and 'old' in cached_values:
            return cached_values['old']
        d = None
        if self.new_values_dict:
            d ={**self.new_values_dict, **self.value}
        if d is None and self.instance:
            d = {**self.instance.as_dict(), **self.value}
        if d is not None:
            self.cache.set(self.pk, {**cached_values, 'old': d})
        return d

    @property
    def new_values_dict(self):
        cached_values = self.cache.get(self.pk, dict())
        if cached_values and 'new' in cached_values:
            return cached_values['new']
        d = None
        if ('cached' in self.next.cached_data) or \
                ('cached' in self.next.next.cached_data) or \
                ('cached' in self.next.next.next.cached_data):
                d = {**self.next.new_values_dict, **self.next.value}
        if d is not None:
            self.cache.set(self.pk, {**cached_values, 'new': d, 'cached': True})
        # cached values to far from this transaction
        if d is None:
            d = self.instance.as_dict()
        return d

    @property
    def field(self):
        if self.value and len(self.value.keys()) == 1:
            return list(self.value.keys())[0]

    @property
    def fields(self):
        if self.value:
            return list(self.value.keys())

    @property
    def task_name(self):
        if self.change_type == self.CREATE:
            return 'task_create'
        elif self.change_type == self.UPDATE:
            if self.field:
                return 'task_update_' + self.field
        elif self.change_type == self.DELETE:
            return 'task_delete'

    @property
    def old_instance(self):
        if self.value is None:
            return None

        instance = self.content_type.model_class()()
        for field in instance._meta.fields:
            try:
                if isinstance(field, models.ForeignKey):
                    setattr(instance, field.name + '_id', self.old_values_dict[field.name])
                else:
                    setattr(instance, field.name, self.old_values_dict[field.name])
            except KeyError:
                setattr(instance, field.name, None)
        return instance

    def get_priority(self):
        if self.instance is None and self.change_type != self.DELETE:
            # empty priority, will never execute
            return 0
        if self.change_type == self.CREATE:
            if hasattr(self.instance, 'task_create_priority'):
                return self.instance.task_create_priority
            else:
                # default for CREATE task
                return 100
        elif self.change_type == self.UPDATE:
            if self.field:
                if hasattr(self.instance, 'task_update_'+self.field):
                    return getattr(self.instance, 'task_update_'+self.field+'_priority')
            # default for UPDATE task
            return 50
        elif self.change_type == self.DELETE:
            if hasattr(self.instance, 'task_delete_priority'):
                return self.instance.task_delete_priority
            else:
                # default for DELETE task
                return 90


    def render_command(self, command):
        """Replaces curly-braced words in `command' with values of corresponding models fields"""
        import string

        if command is None or self.instance is None:
            return
        return command.format(**{
            i[1].split('.')[0]: getattr(self.instance, i[1].split('.')[0])
            for i
            in string.Formatter().parse(command.strip())
            if i is not None and i[1] is not None
            })

    def exec(self, command):
        import subprocess
        import shlex
        import os
        if command:
            rendered_command = self.render_command(command)
            logger.info('Running command {0}'.format(rendered_command))
            with subprocess.Popen(
                            ['sudo'] + shlex.split(rendered_command),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=os.environ.copy()
            ) as p:
                stdout, stderr = p.communicate()
                if p.returncode != 0:
                    raise TaskFailed("Execution of command `{0}' failed with errorcode {1}: {2}".format(
                        rendered_command, p.returncode, stderr))
                return stdout, stderr

    def commit(self):
        logger.info("Executing task for \n"
                    "{transaction}:\n"
                    "instance\t=\t{instance}\n"
                    "content_type\t=\t{content_type}\n"
                    "change_type\t=\t{change_type}\n"
                    "created\t=\t{created}\n"
                    "started\t=\t{started}\n"
                    "committed\t=\t{committed}\n"
                    "rolledback\t=\t{rolledback}\n"
                    "value\t=\t{value}\n"
                    "field\t=\t{field}\n"
                    "task\t=\t{task}\n"
                    "depends\t=\t{depends}\n"
                    "priority\t=\t{priority}\n"
                    "author\t=\t{author}\n"
                    "old_field_value\t=\t{old_field_value}\n"
                    "new_field_value\t=\t{new_field_value}".format(
            transaction=self,
            instance=self.instance,
            content_type=self.content_type,
            change_type=self.change_type,
            created=self.created,
            started=self.started,
            committed=self.committed,
            rolledback=self.rolledback,
            value=self.value,
            field=self.field,
            task=self.task,
            depends=self.depends.all(),
            priority=self.priority,
            author=self.author,
            old_field_value=self.old_values_dict[self.field],
            new_field_value=self.new_values_dict[self.field])
        )

        instance = self.instance
        if self.change_type == Transaction.DELETE:
            instance = self.old_instance

        logger.debug("Getting attribute `{0}' of instance `{1}' and calling it with params `{2}'".format(
            self.task_name, instance, self))
        try:
            getattr(instance, self.task_name)(self)
            logger.debug("Committing changes for {0}".format(self))
            self.committed = timezone.now()
        except BaseException as e:
            logger.exception("Task for {0} `{1}' failed with error `{2}'".format(
                self, self.task_name, e))
            # rolling back changes
            self.rollback()
        finally:
            self.save(force_update=True)

    def rollback(self, **kwargs):
        logger.warning("Rolling back changes for {0}".format(self))
        self.rolledback = timezone.now()
        if self.change_type == self.CREATE:
            # pre_delete signal does not accept 'raw' argument,
            # this hack is for delete without performing any actions
            self.instance.rollback_delete = True
            self.instance.delete()
            self.instance = None
        elif self.change_type == self.UPDATE:
            kwargs['force_update'] = True
            kwargs['update_fields'] = [self.field]
            kwargs['raw'] = True
            self.old_instance.save(self.old_instance, **kwargs)
        else:
            # DELETE cannot be rolledback
            pass
        self.save(force_update=True)

    def __str__(self):
        return "Transaction #{0} for instance `{1}'".format(self.id, self.instance)


class Model(PolymorphicModel):
    """
    An abstract model to inherit for every model that may require execute some python code or shell commands on
    :model:`felis.Model`'s field changing.

    `Signals <https://docs.djangoproject.com/en/dev/topics/signals/>`_ for this model are defined to check every change
    of :model:`felis.Model`'s field and if an instance have a method named 'task_update_<fieldname>' (where <fieldname>
    is the name of field), executes this method. Arguments to this method are:

     function that may be used to execute some shell-code. Takes specially-formatted shell-code string and returns
     it's output

     :model:`felis.Model`'s instance with field's values before change. Old values are stored in a
     :model:`felis.Transaction` instance. Such instance creates every time before :model:`felis.Model`'s field change.

    If several fields was changed in a one-time :model:`felis.Model`.save() then methods will run asynchronously but
    with respecting of corresponding  'task_update_<fieldname>_priority' value. Higher value means greater priority.
    Methods with lower priorities will synchronously wait for methods with higher priority to complete.

    Priorities allows one-time set quota and rename `zfs(8) <https://www.freebsd.org/cgi/man.cgi?query=jail>`_
    filesystem via :model:`felis.Filesystem`'s instance or change property and start
    `jail(8) <https://www.freebsd.org/cgi/man.cgi?query=jail>`_ via :model:`felis.Jail`.
    """

    class Meta:
        verbose_name = 'Abstracted Model'

    # name = models.CharField(max_length=1024, blank=False, null=False)

    def get_field_tasks(self):

        taskdict = dict()
        for field in self._meta.fields:
            taskname = 'task_update_' + field.name
            priorityname = taskname + '_priority'

            if hasattr(self, taskname):
                if hasattr(self, priorityname):
                    priority = getattr(self, priorityname)
                else:
                    # FIXME: merge with constants in Transaction
                    priority = 50
            else:
                priority = 0

            if priority not in taskdict:
                taskdict[priority] = set()

            taskdict[priority].add(field.name)

        tasklist = list()
        for priority in reversed(sorted(taskdict.keys())):
            for field in taskdict[priority]:
                tasklist.append((priority, field))
        return tasklist

    def save(self, *args, **kwargs):
        if kwargs.get('raw', False):
            self.raw_save = True
        super(Model, self).save()

    def save_base(self, *args, **kwargs):
        if hasattr(self, 'raw_save') and self.raw_save:
            kwargs['raw'] = True
        super(Model, self).save_base(*args, **kwargs)

    def as_dict(self):
        return {
            field.name:
                getattr(self, field.name).pk
                if isinstance(getattr(self, field.name), models.Model)
                else getattr(self, field.name)
            for field
            in self._meta.fields
        }


class FSMMixin(models.Model):
    """
    Mixin to add a state change callbacks in style of transactions
    allowed_state_change is a table of allowed state changes for FSM where None
     have special meaning of 'any state'
    """

    class Meta:
        abstract = True
        verbose_name = 'Model with state storing'

    status = 0  # override this value with choice-able field
    states = (
        (0, 'State one'),
        (1, 'State two'),
        (2, 'State three'),
    )
    allowed_state_changes = {
        (0, 1),
        (1, 2),
        (2, 0)
    }

    def __init__(self, *args, **kwargs):
        self.old_status = None
        super(FSMMixin, self).__init__(*args, **kwargs)


    def statusname(self, s):
        for k, v in self.states:
            if k == s: return v.lower().replace(' ', '_')

    @property
    def status_displayname(self):
        return {k: v  for k, v in self.states}[self.status]

    def switch_status(self, old, new, t):
        """
        Checking whether status change is correct and calling corresponding callback
        Will raise FSMError otherwise which initiate transaction rollback
        """
        allowed = False
        for o, n in self.allowed_state_changes:
            if (o is None) and (n == new):
                allowed = True
            elif (old == o) and (n is None):
                allowed = True
            elif (old == o) and (new == n):
                allowed = True

        if not allowed:
            raise FSMError(
                "State change for field `status' from `{0}' to `{1}' is not allowed".format(
                    self.statusname(old), self.statusname(new)))
        callback_name = 'task_update_status_'+self.statusname(old)+'_'+self.statusname(new)
        if getattr(self, callback_name) and callable(getattr(self, callback_name)):
            getattr(self, callback_name)(t)

    def task_update_status(self, t):
        self.switch_status(t.old_instance.status, self.status, t)
        self.save(update_fields=('status', ))