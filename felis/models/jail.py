# -*- coding: utf-8 -*-

import os
import os.path
from time import sleep
from logging import getLogger
from django.db import models
from django.conf import settings
from django.template import Template, Context
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from .zfs import *
from .rctl import *
from .transaction import FSMMixin
from felis.errors import *

__all__ = ['World', 'Skel', 'Jail']

logger = getLogger('felis.models')



class WorldFSMMixin(FSMMixin):
    class Meta:
        abstract = True
        verbose_name = 'Model with updating_... and updated states'

    UPDATED = 0
    UPDATING = 6
    UPDATING_SRC = 1
    BUILDING_WORLD = 2
    PACKAGING_WORLD = 3
    INSTALLING_WORLD = 4
    CLEANING_UP = 5
    UPDATE_FAILED = 7

    states = (
        (UPDATED, 'Updated'),
        (UPDATING, 'Updating'),
        (UPDATING_SRC, 'Updating sources'),
        (BUILDING_WORLD, 'Building world'),
        (PACKAGING_WORLD, 'Packaging world'),
        (INSTALLING_WORLD, 'Installing world'),
        (CLEANING_UP, 'Cleaning up'),
    )
    allowed_state_changes = {
        (UPDATED, UPDATING),
        (UPDATE_FAILED, UPDATING),
        (UPDATING, UPDATING_SRC),
        (UPDATING_SRC, BUILDING_WORLD),
        (BUILDING_WORLD, PACKAGING_WORLD),
        (PACKAGING_WORLD, INSTALLING_WORLD),
        (INSTALLING_WORLD, CLEANING_UP),
        (CLEANING_UP, UPDATED),
        (None, UPDATE_FAILED),
    }
    status = models.PositiveSmallIntegerField(default=UPDATED, choices=states)

    scriptpath = os.path.join(settings.FELIS_SCRIPTS_DIR, 'rebuild_world.sh')


class World(Filesystem, WorldFSMMixin):
    """
    Represents a FreeBSD world stored in a ZFS filesystem.
    Used to nullfs-mount to jails so many jails can be easily updated
    Inherited from :model:`felis.Filesystem`
    """

    class Meta:
        verbose_name = 'World'

    src_conf = models.TextField(null=True, blank=True)
    make_conf = models.TextField(null=True, blank=True)

    # Tasks

    def task_update_status_updated_updating(self, t):
        self.status = self.UPDATING_SRC

    task_update_status_update_failed_updating = task_update_status_updated_updating

    def task_update_status_updating_updating_src(self, t):
        try:
            t.exec(self.scriptpath+' updatesrc')
            self.status = self.BUILDING_WORLD
        except BaseException as e:
            logger.exception('Cannot update world sources for world {0}: {1}'.format(self, e))
            self.status = self.UPDATE_FAILED

    def task_update_status_updating_src_building_world(self, t):
        try:
            t.exec(self.scriptpath+' buildworld')
            self.status = self.PACKAGING_WORLD
        except BaseException as e:
            logger.exception('Cannot build world {0}: {1}'.format(self, e))
            self.status = self.UPDATE_FAILED

    def task_update_status_building_world_packaging_world(self, t):
        try:
            t.exec(self.scriptpath+' packageworld')
            self.status = self.INSTALLING_WORLD
        except BaseException as e:
            logger.exception('Cannot package world {0}: {1}'.format(self, e))
            self.status = self.UPDATE_FAILED

    def task_update_status_packaging_world_installing_world(self, t):
        try:
            if self.jails.filter(~models.Q(status=Jail.STOPPED)).first():
                jails = [j for j in self.jails.filter(status=Jail.RUNNING)]
                for j in jails:
                    j.status = Jail.STOPPED
                    j.save(update_fields=('status', ))
                sleep(10)  # waiting for jails to stop
                if self.jails.filter(~models.Q(status=Jail.STOPPED)).first():
                    logger.critical("Jails {0} have been stopped, but world {1} updating failed".format(jails, self))
                    raise WorldError('World {0} updating failed as jails refuses to stop.')
            t.exec(self.scriptpath+' installworld')
            self.status = self.CLEANING_UP
        except BaseException as e:
            logger.exception('Cannot install world {0}: {1}'.format(self, e))
            self.status = self.UPDATE_FAILED

    @models.permalink
    def get_absolute_url(self):
        return 'world', (), {'pk': self.pk}


class JailPropertiesMixin(models.Model):
    """
    Stores FreeBSD jail's properties.

    Inherited by :model:`felis.Jail` and :model:`felis.Skel`
    """
    class Meta:
        abstract = True

    @property
    def mounts(self):
        from felis.utils import render_command
        return [render_command(self, i.strip()) for i in self.mount.split('\n') if i]

    # fields that may be overridden by skel's fields values if their value is None
    jail_property_fields = [
        'domainname',
        'exec_system_user',
        'exec_jail_user',
        'exec_start',
        'exec_stop',
        'mount_devfs',
        'mount_fdescfs',
        'mount_procfs',
        'devfs_ruleset',
        'enforce_statfs',
        'allow_raw_sockets',
        'allow_socket_af',
        'allow_set_hostname',
        'allow_sysvipc',
        'allow_mount',
        'allow_mount_zfs',
        'allow_mount_procfs',
        'allow_mount_devfs',
        'allow_chflags'
    ]
    domainname = models.CharField(
        max_length=256, null=True, blank=True, verbose_name='host.domainname', help_text='Domain name')
    exec_system_user = models.CharField(
        max_length=256, null=True, blank=True, verbose_name='exec.system_user',
        help_text='The user name from host environment as whom jailed commands should run')
    exec_jail_user = models.CharField(
        max_length=256, null=True, blank=True, verbose_name='exec.jail_user',
        help_text='The user name from the jailed environment as whom jailed commands should run')
    exec_start = models.CharField(
        max_length=1024, null=True, blank=True, verbose_name='exec.start',
        help_text='Command(s) to run in the jail environment when a jail is created')
    exec_stop = models.CharField(
        max_length=1024, null=True, blank=True, verbose_name='exec.stop',
        help_text='Command(s) to run in the jail environment before a jail is removed')
    mount = models.TextField(
        null=True, blank=True, verbose_name='mount',
        help_text='Filesystems to mount before creating the jail in fstab(5) format')
    mount_devfs = models.NullBooleanField(
        verbose_name='mount.devfs', help_text='Mount a devfs(5) filesystem on the chrooted /dev directory')
    mount_fdescfs = models.NullBooleanField(
        verbose_name='mount.fdescfs', help_text='Mount a fdescfs(5) filesystem on the chrooted /dev/fd directory')
    mount_procfs = models.NullBooleanField(
        verbose_name='mount.procfs', help_text='Mount a procfs(5) filesystem on the chrooted /proc directory')
    devfs_ruleset = models.SmallIntegerField(
        null=True, blank=True, verbose_name='devfs_ruleset',
        help_text='The number of the devfs ruleset that is enforced for mounting devfs in this jail (0 = no ruleset)')
    enforce_statfs = models.SmallIntegerField(
        null=True, blank=True, verbose_name='enforce_statfs',
        help_text='Determines what information processes in a jail are able to get about mount points')
    allow_raw_sockets = models.NullBooleanField(
        verbose_name='allow.raw_sockets',
        help_text='Allows jail operates on raw socket. Required for ping(8) or traceroute(8) to work in jail')
    allow_socket_af = models.NullBooleanField(
        verbose_name='allow.socket_af', help_text='Allows protocols other than IPv4, IPv6, UNIX or route')
    allow_set_hostname = models.NullBooleanField(
        verbose_name='allow.set_hostname', help_text='Allows changing hostname from inside of jail')
    allow_sysvipc = models.NullBooleanField(
        verbose_name='allow.sysvipc', help_text='Allows processes in jail to access System V IPC primitives')
    allow_mount = models.NullBooleanField(
        verbose_name='allow.mount', help_text='Allows privileged user in jail to mount and umount filefystems')
    allow_mount_zfs = models.NullBooleanField(
        verbose_name='allow.mount.zfs', help_text='Allows privileged user in jail to mount and umount ZFS filefystems')
    allow_mount_procfs = models.NullBooleanField(
        verbose_name='allow.mount.procfs', help_text='Allows privileged user in jail to mount and umount procfs')
    allow_mount_devfs = models.NullBooleanField(
        verbose_name='allow.mount.devfs', help_text='Allows privileged user in jail to mount and umount devfs')
    allow_chflags = models.NullBooleanField(
        verbose_name='allow.chflags', help_text='Allows privileged user in jail to manipulate system file flags')


class Skel(Snapshot, JailPropertiesMixin):
    """
    Represents a jail's filesystem skeleton stored in ZFS snapshot
    to make clones for creating new jails
    """

    class Meta:
        verbose_name = 'Skel'

    def clean_fields(self, *args, **kwargs):
        for field in self.jail_property_fields:
            if getattr(self, field) is None or getattr(self, field) == '':
                raise ValidationError({field: [_('Jail properties cannot be empty for Skel instance'), ]})
        super(Skel, self).clean_fields(*args, **kwargs)

    @property
    def jails(self):
        return Jail.objects.filter(base=self)

    @property
    def jail_config(self):
        properties = {
            self._meta.get_field(i).verbose_name: getattr(self, i)
            for i in self.jail_property_fields
            }
        return Template('''
        * {
            {% for field, value in properties.items %}{{ field}} = "{{ value }}";
            {% endfor %}
            {% for m in skel.mounts %}mount += "{{ m }}";
            {% endfor %}
        }
        {% for jail in skel.jails.all %}{{ jail.jail_config }}
        {% endfor %}
        ''').render(Context({
                'skel': self,
                'properties': properties,
            }))

    @property
    def config_file(self):
        confdir = os.path.join(settings.FELIS_WORK_DIR, 'jail.conf.d')
        if not os.path.isdir(confdir):
            os.mkdir(confdir, mode=0o770)
        return os.path.join(confdir, str(self.pk)+'_'+self.name+'.conf')

    def create_config_file(self):
        with open(self.config_file, 'w') as fd:
            fd.write(self.jail_config)

    @models.permalink
    def get_absolute_url(self):
        return 'skel', (), {'pk': self.pk}

    # TASKS

    # cause of inheritance `delete' task will be executed also for Filesystem instance
    # so we need to override task to None to avoid double execution of task
    task_delete = None



class JailFSMMixin(FSMMixin):
    class Meta:
        abstract = True
        verbose_name = 'Model with running/stopped states'

    STOPPED = 0
    RUNNING = 1
    STARTING = 2
    STOPPING = 3

    states = (
        (RUNNING, 'Running'),
        (STOPPED, 'Stopped'),
        (STARTING, 'Starting'),
        (STOPPING, 'Stopping')
    )

    status = models.PositiveSmallIntegerField(default=STOPPED, choices=states)

    # FSM lifecycle is STOPPED -> STARTING -> RUNNING -> STOPPING -> STOPPED
    allowed_state_changes = {
        (RUNNING, STOPPING),
        (STOPPING, STOPPED),
        (STOPPED, STARTING),
        (STARTING, RUNNING),
    }

    # Tasks

    def task_update_status_stopped_starting(self, t):
        self.task_pre_start(t)
        self.task_start(t)
        self.status = self.RUNNING
        self.old_status = self.STARTING

    def task_update_status_starting_running(self, t):
        self.task_post_start(t)

    def task_update_status_running_stopping(self, t):
        self.task_pre_stop(t)
        self.task_stop(t)
        self.status = self.STOPPED
        self.old_status = self.STOPPING

    def task_update_status_stopping_stopped(self, t):
        self.task_post_stop(t)

    # this methods should be overridden
    def task_start(self, t):
        pass
    def task_stop(self, t):
        pass
    def task_post_start(self, t):
        pass
    def task_post_stop(self, t):
        pass
    def task_pre_start(self, t):
        pass
    def task_pre_stop(self, t):
        pass


class Jail(Clone, RctlMixin, JailPropertiesMixin, JailFSMMixin):
    """
    Represents FreeBSD jail.

    Inherits :model:`felis.Clone` as jail is creating by cloning a ZFS snapshot (represented by :model:`felis.Skel`) and
    :model:`felis.JailPropertyMixin` to store jail's properties
    """

    class Meta:
        verbose_name = 'Jail'
        permissions = (('get_console','Can run shhd(8) daemon to get console access'), )

    jid = models.IntegerField(blank=True, null=True)
    world_template = models.ForeignKey(World, related_name='jails', null=True)
    console = models.BooleanField(default=False)

    @property
    def skel(self):
        return Skel.objects.get(pk=self.base_id)

    @property
    def jail_config(self):
        properties = {
            self._meta.get_field(i).verbose_name: getattr(self, i)
            for i in self.jail_property_fields
            if getattr(self, i) is not None and getattr(self, i)
            }

        return Template(''.join((
            """\n""",
            """{{ jail.name }} {\n""",
            """\thost.hostname = "{{ jail.name }}";\n""",
            """{% for ip in jail.addresses.all %}""",
            """\t{% if ip.protocol == 4 %}ip4.addr{% else %}ip6.addr{% endif %}""",
            """+= "{{ ip.interface.name }}|{{ ip.address }}/{{ ip.netmask }}";\n""",
            """{% endfor %}""",
            """{# jid = "{{ pk }}"; #}""",
            """\tpath = "{{ jail.path }}";\n""",
            """{% for m in jail.mounts %}\tmount += "{{ m }}";\n""",
            """{% endfor %}""",
            """{% for field, value in properties.items %}\t{{ field }} = "{{ value }}";\n""",
            """{% endfor %}""",
            """}\n""",
        ))).render(Context({
            'jail': self,
            'properties': properties,
        }))

    @models.permalink
    def get_absolute_url(self):
        return 'jail', (), {'pk': self.pk}

    def __str__(self):
        return 'jail #{0}: {1}'.format(self.pk, self.name)

    # TASKS

    def task_delete(self, t):
        # TODO: need testing
        self.status = self.STOPPED
        self.save()
    task_delete_priority = 60

    def task_pre_start(self, t):
        self.skel.create_config_file()

    def task_start(self, t):
        logger.info('Starting jail {0}'.format(self))
        stdout, _stderr = t.exec('jail -i -cmr -f {skel.config_file} {name}')
        self.jid = int(stdout.split(b'\n')[0])

    def task_post_start(self, t):
        logger.info('Jail {0} started'.format(self))

    def task_pre_stop(self, t):
        logger.debug("Setting console to False before stop for jail {0}".format(self))
        self.console = False

    def task_stop(self, t):
        logger.info('Stopping jail {0}'.format(self))
        try:
            t.exec('jail -r -f {skel.config_file} {name}')
        except TaskFailed:
            pass

    def task_post_stop(self, t):
        self.jid = None
        logger.info('Jail {0} stopped'.format(self))

    task_update_status_priority = 70

    def task_update_console(self, t):
        from felis.sshd import SshDaemon
        sshd = SshDaemon(self)
        if self.console:
            if self.status != self.RUNNING:
                raise JailError('Cannot start console for stopped jail')
            # console status set to opened. Running sshd
            logger.info('Starting sshd daemon for jail {0}'.format(self))
            logger.debug('sshd daemon command: {0}'.format(sshd.command_string))
            sshd.start()
            # setting console status to closed as sshd was killed

        else:
            logger.info("Stopping sshd daemon for jail {0}".format(self))
            sshd.kill()


