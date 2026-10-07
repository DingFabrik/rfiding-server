from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .esphome import bridge
from .models import Machine


@receiver(post_save, sender=Machine)
@receiver(post_delete, sender=Machine)
def notify_machine_manager(sender, instance, **kwargs):
    """Lets the machine manager reconnect or push the new config right away."""
    if bridge.is_enabled():
        pk = instance.pk
        transaction.on_commit(lambda: bridge.notify_machine_changed(pk))
