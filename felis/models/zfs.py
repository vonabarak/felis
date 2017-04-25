# -*- coding: utf-8 -*-

from django.db import models
from django.utils.translation import ugettext_lazy as _
from .transaction import Model

__all__ = ['Filesystem', 'Snapshot', 'Clone']

class Filesystem(Model):
    """
    Represents ZFS filesystem.

    Changing fields like  ``name`` or ``quota`` triggers executing
    `zfs(8) <https://www.freebsd.org/cgi/man.cgi?query=jail>`_ rename or
    `zfs(8) <https://www.freebsd.org/cgi/man.cgi?query=jail>`_ set quota correspondingly.
    """

    class Meta:
        verbose_name = 'File system'
        unique_together = (('parent', 'name'),)

    name = models.CharField(max_length=1024, blank=False, null=False)
    description = models.TextField(null=True, blank=True)
    quota = models.BigIntegerField(
        null=True, blank=True, default=None, help_text=_('Filesystem size in bytes'))
    parent = models.ForeignKey(
        'self', related_name='subfilesystems', on_delete=models.PROTECT,
        null=True, blank=True, help_text='Parent filesystem')
    mountpoint = models.CharField(
        max_length=1024, blank=True, null=True, default=None, help_text=_('May not conside with ZFS path'))

    used = models.BigIntegerField(null=True, editable=False)
    avail = models.BigIntegerField(null=True, editable=False)
    refer = models.BigIntegerField(null=True, editable=False)

    def clean(self):
        if self.parent and self.parent.quota and self.quota and self.quota > self.parent.quota:
            self.quota = self.parent.quota
            # raise ValidationError(
            #     _('Quota must be less than or equal to quota of parent filesystem. '
            #       'Parent quota is {0}'.format(self.parent.quota_prefixed)),
            #     'quota_error',
            #     params={'parent_quota': self.parent.quota, 'quota': self.quota}
            # )
        super(Filesystem, self).clean()

    @property
    def quota_prefixed(self):
        from felis.utils import size_prefixed
        return size_prefixed(self.quota)

    @property
    def path(self):
        """Returns unix path of mounted filesystem"""
        if self.mountpoint:
            return self.mountpoint
        elif self.parent:
            return self.parent.path + '/' + self.name
        else:
            return '/' + self.name

    @property
    def zpath(self):
        """Returns ZFS path of filesystem"""
        if not self.parent:
            return self.name
        else:
            return self.parent.zpath + '/' + self.name

    def __str__(self):
        return 'filesystem #{0}: {1}'.format(self.pk, self.name)

    # tasks
    def task_update_name(self, t):
        t.exec('zfs rename ' + t.old_instance.zpath + ' {zpath}')
    task_update_name_priority = 80

    def task_update_quota(self, t):
        t.exec('zfs set quota={quota_prefixed} {zpath}')
    task_update_quota_priority = 20

    def task_update_mountpoint(self, t):
        if not self.mountpoint:
            t.exec('zfs set mountpoint=none {zpath}')
        else:
            t.exec('zfs set mountpoint={mountpoint} {zpath}')
    task_update_mountpoint_priority = 30

    def task_create(self, t):
        if self.parent is None:
            # only root volume dont havea parent
            return None

        if self.mountpoint:
            mountpoint = '-o mountpoint={mountpoint} '
        else:
            mountpoint = ' '

        if self.quota:
            quota = '-o quota={quota_prefixed} '
        else:
            quota = ' '
        t.exec('zfs create ' + mountpoint + quota + '{zpath} ')
    task_create_piority = 100

    def task_delete(self, t):
        return t.exec('zfs destroy {zpath}')
    task_delete_priority = 90

    @models.permalink
    def get_absolute_url(self):
        return 'filesystem', (), {'pk': self.pk}

    def make_snapshot(self, name):
        return Snapshot.objects.create(base=self, name=name)


class Snapshot(Model):
    """
    Represents ZFS snapshot
    """
    class Meta:
        verbose_name = 'Snapshot'
        unique_together = (('base', 'name'),)

    name = models.CharField(max_length=1024, blank=False, null=False)
    description = models.TextField(null=True, blank=True)
    base = models.ForeignKey(Filesystem, on_delete=models.PROTECT, related_name='snapshots')

    @property
    def zpath(self):
        if self.base is None:
            return None
        else:
            return self.base.zpath + '@' + self.name

    def __str__(self):
        return 'snapshot #{0}: {1}'.format(self.pk, self.name)

    # tasks
    def task_update_name(self, t):
        t.exec('zfs rename ' + t.old_instance.zpath + ' {zpath}')
    task_update_name_priority = 80

    def task_update_base(self, t):
        raise ValueError('Cannot change base of snapshot')

    def task_create(self, t):
        t.exec('zfs snapshot {zpath}')

    def task_delete(self, t):
        t.exec('zfs destroy {zpath}')

    def make_clone(self, parent, name):
        return Clone.objects.create(base=self, parent=parent, name=name)


class Clone(Filesystem):
    """
    Represents clone of ZFS filesystem's snapshot which in order also is a :model:`felis.Filesystem`
    """

    class Meta:
        verbose_name = 'Clone'

    base = models.ForeignKey(Snapshot, on_delete=models.PROTECT, related_name='clones')

    # tasks
    task_delete = None

    def task_create(self, t):
        return t.exec('zfs clone {base.zpath} {zpath}')

def update_current_zfs_statistics():
    from felis.utils import run_shell_command
    from felis.errors import ZfsStatUpdateFailed
    errcode, stdout, stderr = run_shell_command('zfs list -Hp')
    if errcode != 0:
        raise ZfsStatUpdateFailed()
    stats = list(map(
        lambda x: (x[0].decode('utf-8'), int(x[1]), int(x[2]), int(x[3])),
        [i.split(b'\t') for i in stdout.split(b'\n') if i]
    ))
    for fs in Filesystem.objects.all():
        for s in stats:
            if fs.zpath == s[0]:
                fs.used, fs.avail, fs.refer = s[1:4]
                fs.save()
