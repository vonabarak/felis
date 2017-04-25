import logging
from django.db import models
from django.utils.translation import ugettext_lazy as _

LOG_LEVELS = (
    (logging.NOTSET, _('NotSet')),
    (logging.INFO, _('Info')),
    (logging.WARNING, _('Warning')),
    (logging.DEBUG, _('Debug')),
    (logging.ERROR, _('Error')),
    (logging.FATAL, _('Fatal')),
)


class StatusLog(models.Model):
    logger_name = models.CharField(max_length=128)
    level = models.PositiveSmallIntegerField(choices=LOG_LEVELS, default=logging.ERROR, db_index=True)
    msg = models.TextField()
    trace = models.TextField(blank=True, null=True)
    viewed = models.BooleanField(default=False, db_index=True)
    ctime = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.msg

    class Meta:
        ordering = ('-ctime',)
        app_label = 'selfcheck'
