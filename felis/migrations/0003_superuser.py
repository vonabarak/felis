# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from django.db import migrations


def create_superuser(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    User = apps.get_model("auth", "User")
    u = User.objects.using(db_alias).create(
        username='felis',
        email='felis@vonabarak.ru',
        first_name='Felis',
        last_name='Silvestris',
        is_staff=True,
        is_superuser=True,
        password='pbkdf2_sha256$30000$GqbxNFi5p9dc$zEl6q00MUndG0v8SDPQtU0IXmKC/k0oCt0FcUXksh34=',
    )


class Migration(migrations.Migration):

    initial = False

    dependencies = [
        ('felis', '0002_scheduled_task'),
    ]

    operations = [
        migrations.RunPython(create_superuser)
    ]
