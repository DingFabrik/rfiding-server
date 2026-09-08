from django.core.cache import cache
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Holiday(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Name"))
    date = models.DateField(unique=True, verbose_name=_("Date"))
    repeats_annually = models.BooleanField(default=False, verbose_name=_("Repeats Annually"))

    class Meta:
        verbose_name = _("Holiday")
        verbose_name_plural = _("Holidays")
        ordering = ["date"]

    def __str__(self):
        return f"{self.name} on {self.date}"


@receiver(post_save, sender=Holiday)
@receiver(post_delete, sender=Holiday)
def invalidate_is_today_holiday(sender, instance, **kwargs):
    from .utils import is_today_holiday_cache_key

    cache.delete(is_today_holiday_cache_key(timezone.localdate()))