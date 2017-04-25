# -*- coding: utf-8 -*-

from felis.models import *
import time
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
import logging
from django_q.tasks import async, fetch

logger = logging.getLogger(__name__)

TRANSACTION_COMMIT_TIMEOUT = timedelta(hours=4)

def task_scheduler():
    logger.debug('Checking for tasks to run...')
    time.sleep(2)  # to ensure most changes have been written
    try:
        # filtering out transactions which instance have been deleted to avoid circular-dependencies
        #for transaction in Transaction.objects.filter(~Q(change_type=Transaction.DELETE) & Q(instance__isnull=True)):
        #    transaction.delete()

        # selecting all transactions need to run
        for transaction in Transaction.objects.filter(
            Q(committed=None) &
            Q(rolledback=None) &
            Q(started=None) &
            Q(priority__gt=0)
        ).order_by('-priority').all():
            # filtering out transactions with unfinished dependencies
            if not transaction.depends.filter(
                Q(committed=None)
                & Q(rolledback=None)
                & Q(priority__gt=transaction.priority)
            ).first():
                # delaying task to next iteration if there is running tasks with same instance

                if Transaction.objects.filter(
                                        Q(committed=None)
                                        & Q(rolledback=None)
                                        & ~Q(started=None)
                                        & Q(priority__gt=0)
                                        & Q(instance=transaction.instance)):
                    logger.debug('Delaying {0} as there is another transaction on {1} already running'.format(
                        transaction, transaction.instance))
                    continue
                transaction.started = timezone.now()
                transaction.task = fetch(async(transaction.commit))
                transaction.save(force_update=True)
            elif transaction.depends.filter(~Q(rolledback=None) & Q(priority__gt=transaction.priority)).first():
                    logger.debug('Rolling back {0} as its dependency {1} have been rolled back'.format(
                        transaction,
                        transaction.depends.filter(~Q(rolledback=None) & Q(priority__gt=transaction.priority)).first())
                    )
                    transaction.rollback()
            else:
                logger.debug('Waiting for {0} to commit'.format(
                    transaction.depends.filter(Q(committed=None) & Q(priority__gt=transaction.priority)).all()))
        for transaction in Transaction.objects.filter(
            Q(committed=None) &
            Q(rolledback=None) &
            ~Q(started=None) &
            Q(started__lt=timezone.now() - TRANSACTION_COMMIT_TIMEOUT)
        ):
            transaction.rollback()
    except BaseException as e:
        logger.exception('An Exception {0} occured trying to run task'.format(e))
    logger.debug('No tasks left to run.')
