# -*- coding: utf-8 -*-

import logging
from django.conf.urls import url, include
from django.contrib.auth.models import User
from rest_framework import routers, serializers, viewsets
from felis.models import *

__all__ = ['FelisViewSet', 'router']

class FelisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Model
        fields = '__all__'

class JailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Jail
        fields = '__all__'


class FilesystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Filesystem
        fields = '__all__'


class WorldSerializer(serializers.ModelSerializer):
    class Meta:
        model = World
        fields = '__all__'


class SkelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skel
        fields = '__all__'


class FelisViewSet(viewsets.ModelViewSet):
    queryset = Model.objects.all()
    serializer_class = FelisSerializer


class JailViewSet(viewsets.ModelViewSet):
    queryset = Jail.objects.all()
    serializer_class = JailSerializer


class FilesystemViewSet(viewsets.ModelViewSet):
    queryset = Filesystem.objects.all()
    serializer_class = FilesystemSerializer


class WorldViewSet(viewsets.ModelViewSet):
    queryset = World.objects.all()
    serializer_class = WorldSerializer


class SkelViewSet(viewsets.ModelViewSet):
    queryset = Skel.objects.all()
    serializer_class = SkelSerializer


# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r'models', FelisViewSet)
router.register(r'jail', JailViewSet)
router.register(r'filesystem', FilesystemViewSet)
router.register(r'world', WorldViewSet)
router.register(r'skel', SkelViewSet)

