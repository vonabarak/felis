# -*- coding: utf-8 -*-

import os
import os.path
import signal
import subprocess
import shlex

from django.core.cache import caches
from django.conf import settings
from django.contrib.auth import get_user_model
from felis.utils import run_shell_command
from guardian.shortcuts import get_perms
from django_q.tasks import async

class SshDaemon:
    """
    Class represents sshd(8) daemon
    """

    def __init__(self, jail):
        self.cachename = 'sshd'
        self.jail = jail
        self.piddir = os.path.join(settings.FELIS_WORK_DIR, 'sshd.pid.d')
        self.hostkeydir = os.path.join(settings.FELIS_WORK_DIR, 'sshd.key.d')
        for d in (self.piddir, self.hostkeydir):
            if not os.path.isdir(d):
                os.mkdir(d, mode=0o770)
        self.pidfile = os.path.join(self.piddir, str(jail.name)+'.pid')
        self.hostkeyfile = os.path.join(self.hostkeydir, str(jail.name)+'_hostkey.pem')
        self.authkeyfile = os.path.join(self.hostkeydir, str(jail.name) + '_authorized_keys')
        self.port = settings.FELIS_SSHD_PORT_OFFSET + jail.pk

    @property
    def cache(self):
        return caches[self.cachename]

    @property
    def pid(self):
        pid = self.cache.get(self.jail.pk, None)
        if not pid:
            if os.path.isfile(self.pidfile):
                try:
                    with open(self.pidfile, 'r') as fh:
                        pid = int(fh.read())
                except ValueError:
                    pass
        return pid

    def regenerate_hostkey(self):
        if not os.path.isfile(self.hostkeyfile):
            run_shell_command('ssh-keygen -P "" -f {0}'.format(self.hostkeyfile), sudo=False)

    def regenerate_authkey(self):
        keys = set()
        for u in get_user_model().objects.all():
            if 'get_console' in  get_perms(u, self.jail):
                if u.preferences and u.preferences.ssh_pubkey:
                    keys.add(u.preferences.ssh_pubkey)

        with open(self.authkeyfile, 'w') as fh:
            fh.writelines(keys)

        os.chmod(self.authkeyfile, 0o600)


    @property
    def command_string(self):
        return ("""/usr/sbin/sshd -D """
                """-o HostKey="{0}" """
                """-o PermitTTY=yes """
                """-o UsePrivilegeSeparation=no """
                """-o PermitUserEnvironment=no """
                """-o AuthorizedKeysFile="{1}" """
                """-o ForceCommand="/usr/local/bin/sudo /usr/sbin/jexec jailone /usr/bin/login -f {2}" """
                """-o Port={3} """
                """-o UsePAM=no """
                """-o PasswordAuthentication=no """
                """-o ChallengeResponseAuthentication=no """
                """-o PidFile="{4}" """
                """-o ClientAliveInterval=300 """  # All clients idle for more than 5 min
                """-o ClientAliveCountMax=0 """    # will be dropped
        ).format(self.hostkeyfile, self.authkeyfile, self.jail.exec_jail_user, self.port, self.pidfile)

    def is_running(self):
        if self.pid:
            code, out, err = run_shell_command('ps -o pid -p {0}'.format(self.pid))
            if str(self.pid) in str(out):
                return True
        return False

    def kill(self):
        try:
            if self.pid:
                os.kill(self.pid, signal.SIGKILL)
            os.unlink(self.pidfile)
        except (FileNotFoundError, ProcessLookupError):
            pass
        self.cache.delete(self.jail.pk)

    def run(self):
        if not self.is_running():
            self.kill()
            self.regenerate_hostkey()
            self.regenerate_authkey()
            with subprocess.Popen(shlex.split(self.command_string)) as p:
                self.cache.set(self.jail.pk, p.pid)

    def on_stop(self, _task):
        # process of django_q may be garbage-collected but sshd daemon must be still running
        # so here we set console as False only if it is really not running
        if not self.is_running():
            self.jail.refresh_from_db()
            self.jail.console = False
            self.jail.save(update_fields=('console', ))

    def start(self):
        async(self.run, hook=self.on_stop)

    def wait(self):
        if self.is_running():
            os.waitpid(self.pid)
