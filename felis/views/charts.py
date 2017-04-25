# -*- coding: utf-8 -*-

from datetime import timedelta
from django.utils import timezone
from django import http
from django.views.generic import View
from felis.models import *

__all__ = ['ChartView', 'RctlChartView', 'RctlIOChartView', 'FSChartView', 'FSDiagramView']

class ChartView(View):

    def get(self, request, pk, attribute, **kwargs):
        import pygal
        from pygal.style import DarkSolarizedStyle
        object = Model.objects.get(pk=pk)
        chartline = pygal.DateTimeLine(
            x_label_rotation=35, truncate_label=-1, style=DarkSolarizedStyle,
            x_value_formatter=lambda dt: dt.strftime('%d, %b %Y at %I:%M:%S %p'),
        )
        dots = [
            (i.created, i.value[attribute])
            for i
            in Transaction.objects.filter(
                instance=object,
                created__gt=timezone.now() - timedelta(hours=6)
            ).order_by('id')
            if hasattr(i, 'value') and attribute in i.value and i.value[attribute] is not None
            ]
        dots.append((timezone.now(), object.as_dict()[attribute]))
        chartline.add(attribute, dots)
        return http.HttpResponse(chartline.render(), content_type='image/svg+xml')


class RctlChartView(View):

    def get(self, request, pk, attribute, **kwargs):
        import pygal
        from pygal.style import DarkSolarizedStyle

        object = Model.objects.get(pk=pk)
        chartline = pygal.DateTimeLine(
            x_label_rotation=35, truncate_label=-1, style=DarkSolarizedStyle, fill=True,
            x_value_formatter=lambda dt: dt.strftime('%d, %b %Y at %I:%M:%S %p'),
        )
        fieldname = 'rctl_' + attribute
        dots = [
            (i.created, i.value[fieldname])
            for i
            in Transaction.objects.filter(
                instance=object,
                created__gt=timezone.now() - timedelta(hours=6)
            ).order_by('id')
            if (fieldname in i.value) and (i.value[fieldname] is not None)
            ]
        dots.append((timezone.now(), object.as_dict()[fieldname]))
        chartline.add(attribute, dots)
        for rule in RctlRule.objects.filter(jail=object, resource=attribute).all():
            chartline.add(
                rule.action,[(timezone.now()-timedelta(hours=6), rule.amount), (timezone.now(), rule.amount)]
            )
        return http.HttpResponse(chartline.render(), content_type='image/svg+xml')


class RctlIOChartView(View):

    def get(self, request, pk, **kwargs):
        import pygal
        from pygal.style import DarkSolarizedStyle

        object = Model.objects.get(pk=pk)
        chartline = pygal.DateTimeLine(
            x_label_rotation=35, truncate_label=-1, style=DarkSolarizedStyle, fill=True,
            x_value_formatter=lambda dt: dt.strftime('%d, %b %Y at %I:%M:%S %p'),
            # interpolate='hermite', interpolation_parameters={'type': 'cardinal', 'c': 0.75},
            legend_at_bottom=True, dots_size=1
        )
        for attribute in ['readbps', 'writebps', 'readiops', 'writeiops']:
            fieldname = 'rctl_' + attribute
            dots = [
                (i.created, i.new_values_dict[fieldname])
                for i
                in Transaction.objects.filter(
                    instance=object,
                    created__gt=timezone.now() - timedelta(hours=1)
                ).order_by('id')
                if (fieldname in i.new_values_dict) and (i.new_values_dict[fieldname] is not None)
                ]
            dots.append((timezone.now(), object.as_dict()[fieldname]))

            if attribute.endswith('iops'):
                secondary = True
            else:
                secondary = False

            chartline.add(attribute, dots, secondary=secondary)
            for rule in RctlRule.objects.filter(jail=object, resource=attribute).all():
                chartline.add(
                    attribute+' '+rule.action,
                    [(timezone.now()-timedelta(hours=1), rule.amount), (timezone.now(), rule.amount)],
                    secondary=secondary
                )
        return http.HttpResponse(chartline.render(), content_type='image/svg+xml')

class FSChartView(View):

    def get(self, request, pk, **kwargs):
        import pygal
        from pygal.style import DarkSolarizedStyle
        chartline = pygal.DateTimeLine(
            x_label_rotation=35, truncate_label=-1, style=DarkSolarizedStyle, logarithmic=True,
            x_value_formatter=lambda dt: dt.strftime('%d, %b %Y at %I:%M:%S %p'), dots_size = 1,
            interpolate='hermite', interpolation_parameters={'type': 'cardinal', 'c': .75},
        )
        object = Model.objects.get(pk=pk)

        used = [
            (i.created, i.value['used'])
            for i
            in Transaction.objects.filter(
                instance=object,
                created__gt=timezone.now() - timedelta(hours=3)
            ).order_by('id')
            if hasattr(i, 'value') and 'used' in i.value and i.value['used'] is not None
            ]
        used.append((timezone.now(), object.used))
        avail = [
            (i.created, i.value['avail'])
            for i
            in Transaction.objects.filter(
                instance=object,
                created__gt=timezone.now() - timedelta(hours=3)
            ).order_by('id')
            if hasattr(i, 'value') and 'avail' in i.value and i.value['avail'] is not None
            ]
        avail.append((timezone.now(), object.avail))
        refer = [
            (i.created, i.value['refer'])
            for i
            in Transaction.objects.filter(
                instance=object,
                created__gt=timezone.now() - timedelta(hours=3)
            ).order_by('id')
            if hasattr(i, 'value') and 'refer' in i.value and i.value['refer'] is not None
            ]
        refer.append((timezone.now(), object.refer))
        chartline.add('USED', used, fill=True)
        chartline.add('AVAIL', avail, fill=True)
        chartline.add('REFER', refer, fill=True)
        return http.HttpResponse(chartline.render(), content_type='image/svg+xml')

class FSDiagramView(View):

    def get(self, request, pk, **kwargs):
        import pygal
        from pygal.style import DarkSolarizedStyle

        object = Filesystem.objects.get(pk=pk)
        diagram = pygal.Pie(style=DarkSolarizedStyle)
        diagram.title = 'File system disk space usage'
        diagram.add('USED (without REFER)', object.used-object.refer)
        diagram.add('REFER', object.refer)
        diagram.add('AVAIL', object.avail)
        return http.HttpResponse(diagram.render(), content_type='image/svg+xml')

