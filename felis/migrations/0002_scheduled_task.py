# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import arrow
from django.db import migrations


def create_scheduled_task(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    Schedule = apps.get_model("django_q", "Schedule")

    # tasks for committing unapplied changesets twice a minute
    #for x in range(0, 60, 30):
    Schedule.objects.using(db_alias).create(
        name='Run tasks for unapplied changesets',
        func='felis.tasks.task_scheduler',
        schedule_type='I',  # 'I' is minutes in Shedule model
        minutes=1,
        repeats=-1,
        next_run=arrow.utcnow().replace(second=0).shift(minutes=1).datetime
    )

    # task to collect consuming resources via rctl
    Schedule.objects.using(db_alias).create(
        name='Collect resource usage statistics for jails',
        func='felis.models.rctl.update_current_rctls',
        schedule_type='I',
        minutes=1,
        repeats=-1,
        next_run=arrow.utcnow().replace(second=10).shift(minutes=1).datetime
    )

    # task to collect zfs space usage statistics
    Schedule.objects.using(db_alias).create(
        name='Collect ZFS disk space usage statistics',
        func='felis.models.zfs.update_current_zfs_statistics',
        schedule_type='I',
        minutes=10,
        repeats=-1,
        next_run=arrow.utcnow().replace(second=20).shift(minutes=1).datetime
    )


class Migration(migrations.Migration):

    initial = False

    dependencies = [
        ('felis', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_scheduled_task)
    ]
