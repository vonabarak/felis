# -*- coding: utf-8 -*-

import subprocess
import re
from time import sleep
from django.test import TestCase
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.forms.models import model_to_dict
from felis.models import *


class FelisModelTests(TestCase):
    fixtures = ['felis.json']

    def setUp(self):
        super(FelisModelTests, self).setUp()
        self.test_filesystem1 = Filesystem.objects.create(
            name='testfilesystem1',
            parent=Filesystem.objects.get(pk=1)
        )

    def test_instance_creating(self):
        f = Filesystem.objects.create(
            name='testfilesystem0',
            parent=None
        )
        cs = f.transactions.first()
        self.assertIsNotNone(cs)
        self.assertEqual(cs.change_type, Transaction.CREATE)

    def test_field_updating(self):
        # from fixtures
        f = Filesystem.objects.get(pk=2)
        f.quota = 2*1024*1024*1024
        f.save()
        cs = f.transactions.first()
        self.assertIsNotNone(cs)
        self.assertEqual(cs.change_type, Transaction.UPDATE)
        self.assertEqual(cs.field, 'quota')
        # old value for quota was None and it must be in serialized copy
        self.assertIsNone(cs.value['quota'])

    def test_instance_deleting(self):
        f = Filesystem.objects.get(name='testfilesystem1')
        serialized = model_to_dict(f, fields=[field.name for field in f._meta.fields])
        f.delete()
        cs = Transaction.objects.filter(instance=None, change_type=Transaction.DELETE).first()
        self.assertIsNotNone(cs)
        self.assertEqual(cs.value['id'], serialized['id'])

    def test_dependencies(self):
        f = Filesystem.objects.get(pk=2)
        f.quota = 3 * 1024 * 1024 * 1024
        f.save()
        f.quota = 4 * 1024 * 1024 * 1024
        f.save()
        css = [i for i in f.transactions.all()]
        self.assertEqual(css[0].value['quota'], 3 * 1024 * 1024 * 1024)
        self.assertEqual(f.transactions.first().depends.first(), None)

    def test_multiple_fields_updating(self):
        f = Filesystem.objects.get(name='multiple_updating_test')
        f.quota = 4 * 1024 * 1024 * 1024
        f.name = 'new_name'
        f.description = 'Test test test'
        f.save()
        self.assertIsNotNone(f.transactions.filter(change_type=Transaction.UPDATE, field='quota').first())
        self.assertIsNotNone(f.transactions.filter(change_type=Transaction.UPDATE, field='name').first())
        self.assertIsNone(f.transactions.filter(change_type=Transaction.UPDATE, field='description').first())
        self.assertIsNotNone(f.transactions.filter(change_type=Transaction.UPDATE, field=None).first())

class FelisMiscTests(TestCase):

    fixtures = ['felis1.json']

    def test_sshd_object(self):
        import os
        import shutil
        from felis.sshd import SshDaemon
        from django.contrib.auth import get_user_model
        u = get_user_model().objects.get(username='felis')  # from fixtures
        s = SshDaemon(Jail.objects.first())
        shutil.rmtree(s.hostkeydir)
        s = SshDaemon(Jail.objects.first())
        s.regenerate_hostkey()
        s.regenerate_authkey()
        self.assertTrue(os.path.isdir(s.hostkeydir))
        self.assertTrue(os.path.isfile(s.authkeyfile))
        self.assertTrue(os.path.isfile(s.hostkeyfile))
        with open(s.authkeyfile, 'r') as fh:
            self.assertEqual(u.prefrences.ssh_pubkey, fh.readline())

# class FelisTests(TestCase):
#     fixtures = ['felis.json']
#
#     def run(command):
#         return subprocess.getoutput('sudo ' + command)
#
#
#
#     # def setUp(self):
#     #     self.filesystem = Filesystem.objects.create(
#     #         name='test_filesystem10',
#     #         parent_id=1,
#     #         mountpoint='/mnt/test_filesystem10',
#     #         quota=2*1024*1024*1024
#     #     )
#     #     sleep(5)
#     #
#     # def _post_teardown(self):
#     #     self.filesystem.delete()
#     #     super(FelisTests, self)._post_teardown()
#
#     def test_filesystem_create_delete(self):
#         f = Filesystem.objects.create(
#             name='test_filesystem11',
#             parent_id=1,
#             mountpoint='/mnt/test_filesystem11',
#             quota=2*1024*1024*1024
#         )
#         sleep(5)
#         self.assertRegex(
#             run('zfs list -H zroot/test_filesystem11'),
#             r'^zroot/test_filesystem11\s+([\d\.]{1,4}[KMG]\s+)(2\.00G\s+)([\d\.]{1,4}[KMG]\s+)/mnt/test_filesystem11$'
#         )
#         f.delete()
#         sleep(5)
#         self.assertTrue(run('zfs list -H zroot/test_filesystem11').startswith('cannot open'))
#
#     # def test_changing_quota_property(self):
#     #     self.assertRegex(
#     #         run('zfs get -H quota zroot/test_filesystem10'),
#     #         r'^zroot/test_filesystem10\s+quota\s+2(\.00)?G\s+'
#     #     )
#     #     self.filesystem.quota = 3*1024*1024*1024
#     #     self.filesystem.save()
#     #     sleep(5)
#     #     self.assertRegex(
#     #         run('zfs get -H quota zroot/test_filesystem10'),
#     #         r'^zroot/test_filesystem10\s+quota\s+3(\.00)?G\s+'
#     #     )
#
#     def test_jail_start_stop(self):
#
#         j = Jail.objects.get(pk=17)
#         j.status = 'R'
#         j.save()
#         sleep(5)
#         self.assertRegex(
#             run('jls | grep testjail11'),
#             r'^\s+\d+\s+[\d\.]+\s+testjail11\s+/opt/felis/jails/testjail11'
#         )
#         j.status = 'S'
#         j.save()
#         sleep(5)
#         self.assertEqual(run('jls -j testjail11 | grep testjail11'), 'jls: jail "testjail1" not found')
