"""felis URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from django.views.generic import RedirectView
from rest_framework import routers
from django.contrib.auth import views as auth_views
from felis.views import *


urlpatterns = [
    url(r'^accounts/login/$', auth_views.login, name='login'),
    url(r'^accounts/logout/$', auth_views.logout, name='logout'),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', admin.site.urls),
    url(r'^favicon\.ico$', RedirectView.as_view(url='/static/img/felis.ico', permanent=True)),
    url(r'^$', HomePageView.as_view(), name='home'),

    # Interfaces
    url(r'^interface/(?P<pk>\d+)', InterfaceDetailView.as_view(), name='interface'),
    url(r'^interface/', InterfaceListView.as_view(), name='interfaces'),

    # IP addresses
    url(r'^ipaddress/(?P<pk>\d+)', IPAddressDetailView.as_view(), name='ipaddress'),
    url(r'^ipaddress/', IPAddressListView.as_view(), name='ipaddresses'),
    # Worlds
    url(r'^world/(?P<pk>\d+)', WorldDetailView.as_view(), name='world'),
    url(r'^world/', WorldListView.as_view(), name='worlds'),

    # Skels
    url(r'^skel/(?P<pk>\d+)', SkelDetailView.as_view(), name='skel'),
    url(r'^skel/', SkelListView.as_view(), name='skels'),

    # Filesystems
    url(r'^filesystem/(?P<pk>\d+)', FilesystemDetailView.as_view(), name='filesystem'),
    url(r'^filesystem/', FilesystemListView.as_view(), name='filesystems'),

    # Jails
    url(r'^jail/(?P<pk>\d+)', JailDetailView.as_view(), name='jail'),
    url(r'^jail/', JailListView.as_view(), name='jails'),

    # Transactions
    url(r'^transactions', TransactionListView.as_view(), name='transactions'),

    # Charts
    url(r'^chart/(?P<pk>\d+)/rctl_iochart', RctlIOChartView.as_view(), name='rctl_io_chart'),
    url(r'^chart/(?P<pk>\d+)/rctl_(?P<attribute>[a-z_-]+)', RctlChartView.as_view(), name='rctl_chart'),
    url(r'^chart/(?P<pk>\d+)/fs_diagram', FSDiagramView.as_view(), name='fs_diagram_chart'),
    url(r'^chart/(?P<pk>\d+)/fs', FSChartView.as_view(), name='fs_chart'),
    url(r'^chart/(?P<pk>\d+)/(?P<attribute>[a-z_-]+)', ChartView.as_view(), name='chart'),

    # API
    # Wire up our API using automatic URL routing.
    # Additionally, we include login URLs for the browsable API.
    url(r'^api/', include(router.urls)),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),


    # Logs
    url(r'^errorlog/', ErrorLogView.as_view(), name='errorlog'),

]
