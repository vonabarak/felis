# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals
import logging
from django.db.models.signals import post_save, pre_delete, pre_save, post_delete
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.db.models import Q
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django_q.tasks import async
from felis.models import Model, Transaction, UserPreferences
from felis.middleware import get_auth_user

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@receiver(user_logged_in)
def create_user_prefrences_user_logged_in_receiver(signal, sender, request, user, **kwargs):
    UserPreferences.objects.get_or_create(user=user)


@receiver(pre_save, sender=Transaction)
def felis_changeset_pre_save_signal_receiver(instance, **kwargs):
    instance.full_clean()


@receiver(post_save, sender=Transaction)
def felis_transaction_post_save_signal_receiver(instance, **kwargs):
    if kwargs['created']:
        # uncommited transaction will be set as dependencies for current transaction
        blocking_dependencies = Transaction.objects.filter(
            Q(instance=instance.instance)
            & Q(committed=None)
            & Q(rolledback=None)
            & Q(priority__gt=instance.priority)
        )
        if blocking_dependencies.first():
            logger.debug(
                "{0} dependencies: {1}".format(instance, blocking_dependencies.all()))
        instance.depends.add(*[i for i in blocking_dependencies.all()])

        if get_auth_user():
            instance.author = get_auth_user()
            instance.save()
        async('felis.tasks.task_scheduler')


@receiver(pre_save)
def felis_abstract_model_pre_save_signal_receiver(instance, **kwargs):
    # print('pre_save', kwargs)

    if kwargs.get('raw', False):
        return
    if kwargs['sender'] == Model or not issubclass(kwargs['sender'], Model):
        return

    # pk will be not None if instance is updating but not creating
    if instance.pk is not None:
        logger.debug("Instance `{0}' of  model `{1}' is about to be updated".format(instance, kwargs['sender']))
        original_instance = kwargs['sender'].objects.get(pk=instance.pk)

        # getting set of changed fields
        fieldnames = set()
        for field in instance._meta.fields:
            old_value = getattr(original_instance, field.name)
            new_value = getattr(instance, field.name)
            if old_value != new_value:
                logger.info("Changing property `{0}' of instance `{1}' class `{2}' from `{3}' to `{4}'".format(
                    field.name, instance, kwargs['sender'], old_value, new_value
                ))
                fieldnames.add(field.name)

        # filter out fields that need to call the callback method as they are non-atomic and needs separate transaction
        fields_with_tasks = set()
        for field in fieldnames.copy():
            taskname = 'task_update_' + field
            if not hasattr(instance, taskname) or not callable(getattr(instance, taskname)):
                # field have no callback method or expected attribute is not callable
                pass
            else:
                fieldnames.remove(field)
                fields_with_tasks.add(field)

        # creating one transaction for all updated fields that do not require running any callbacks
        if fieldnames:
            logger.debug(
                "Creating transaction for updating field(s) {fields} of instance `{instance}', model `{model}' "
                "that do _not_ require any task run".format(fields=fieldnames, instance=instance, model=kwargs['sender']))
            Transaction.cache.set(Transaction.objects.create(
                instance=instance,
                content_type=ContentType.objects.get_for_model(instance),
                change_type=Transaction.UPDATE,
                value={k: v for k, v in original_instance.as_dict().items() if k in fieldnames},
                committed=timezone.now()
            ).pk, {'old': original_instance.as_dict(), 'new': instance.as_dict(), 'cached': True})
        # creating transactions in order of task's priority to make right dependencies of tasks
        for priority, fieldname in [i for i in instance.get_field_tasks() if i[0] > 0]:
            if fieldname in fields_with_tasks:
                logger.debug(
                    "Creating transaction for updating field `{field}' "
                    "of instance `{instance}', model `{model}' that require a task run".format(
                        field=fieldname, instance=instance, model=kwargs['sender']))
                Transaction.cache.set(Transaction.objects.create(
                    instance=instance,
                    content_type=ContentType.objects.get_for_model(instance),
                    change_type=Transaction.UPDATE,
                    value={fieldname: getattr(original_instance, fieldname)},
                    priority=priority
                ).pk, {'old': original_instance.as_dict(), 'new': instance.as_dict(), 'cached': True})
    else:
        logger.debug("Instance `{0}' of  model `{1}' is about to be created".format(instance, kwargs['sender']))


@receiver(post_save)
def felis_abstract_model_post_save_signal_receiver(instance, **kwargs):
    if kwargs.get('raw', False):
        return
    if kwargs['sender'] == Model or not issubclass(kwargs['sender'], Model):
        return

    if kwargs['created']:
        logger.info("Instance `{0}' of  model `{1}' have been created".format(instance, kwargs['sender']))
        logger.debug(
            "Creating transaction for creation instance `{0}' of model `{1}'".format(instance, kwargs['sender']))
        Transaction.cache.set(Transaction.objects.create(
            instance=instance,
            content_type=ContentType.objects.get_for_model(instance),
            change_type=Transaction.CREATE,
            value=None,
        ).pk, {'old': None, 'new': instance.as_dict(), 'cached': True})
    else:
        logger.info("Instance `{0}' of  model `{1}' have been updated".format(instance, kwargs['sender']))
    # starting task scheduler
    # async('felis.tasks.task_scheduler')


@receiver(pre_delete)
def felis_abstract_model_pre_delete_signal_receiver(instance, **kwargs):
    # pre_delete signal does not accept 'raw' argument,
    # this hack is for delete without performing any actions
    if hasattr(instance, 'rollback_delete') and getattr(instance, 'rollback_delete'):
        return
    if kwargs['sender'] == Model or not issubclass(kwargs['sender'], Model):
        return
    # print('pre_delete', kwargs)
    logger.info("Instance `{0}' of  model `{1}' is about to be deleted".format(instance, kwargs['sender']))
    logger.debug(
        "Creating transaction for deleting instance `{0}' of model `{1}'".format(instance, kwargs['sender']))
    Transaction.cache.set(Transaction.objects.create(
        instance=None,
        content_type=ContentType.objects.get_for_model(instance),
        change_type=Transaction.DELETE,
        value=instance.as_dict(),
    ).pk, {'old': instance.as_dict(), 'new': None, 'cached': True})


@receiver(post_delete)
def felis_abstract_model_post_delete_signal_receiver(instance, **kwargs):
    # print('post_delete', kwargs)
    if kwargs['sender'] == Model or not issubclass(kwargs['sender'], Model):
        return
    logger.info("Instance `{0}' of  model `{1}' have been deleted".format(instance, kwargs['sender']))
    # starting task scheduler
    # async('felis.tasks.task_scheduler')
