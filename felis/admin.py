# -*- coding: utf-8 -*-

from polymorphic.admin import PolymorphicParentModelAdmin, PolymorphicChildModelAdmin, PolymorphicChildModelFilter
from django.contrib import admin
from felis.models import *
from felis.models import Model


@admin.register(Model)
class ModelAParentAdmin(PolymorphicParentModelAdmin):
    """ The parent model admin """
    base_model = Model
    child_models = (Filesystem, Snapshot, Clone, World, Skel, Jail, Interface, RctlRule)
    list_filter = (PolymorphicChildModelFilter,)  # This is optional.


# @admin.register(Filesystem)
# class FilesystemAdmin(PolymorphicChildModelAdmin):
#     base_model = Filesystem
#
#
# @admin.register(World)
# class FilesystemAdmin(PolymorphicChildModelAdmin):
#     base_model = World

admin.site.register(UserPreferences)
admin.site.register(Filesystem)
admin.site.register(World)
admin.site.register(Skel)
admin.site.register(Jail)
admin.site.register(Interface)
admin.site.register(IPAddress)
admin.site.register(Clone)
admin.site.register(Snapshot)
admin.site.register(Transaction)
admin.site.register(RctlRule)
