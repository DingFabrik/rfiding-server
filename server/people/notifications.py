import logging

from .conf import PERSON_ENABLE_EMAIL, PERSON_ENABLE_SLACK_EMAIL
from .notifiers import EmailNotifier, SlackNotifier

logger = logging.getLogger(__name__)


def get_person_notifiers():
    notifiers = []
    if PERSON_ENABLE_EMAIL:
        notifiers.append(EmailNotifier())
    if PERSON_ENABLE_SLACK_EMAIL:
        notifiers.append(SlackNotifier())
    return notifiers


def notify_person(person, notification_type, context=None):
    """Send `notification_type` to `person` over every enabled, reachable channel.

    Returns the list of channel names a notification was actually sent through.
    """
    sent_via = []
    for notifier in get_person_notifiers():
        try:
            if notifier.send(person, notification_type, context):
                sent_via.append(notifier.channel)
        except Exception:
            logger.exception(
                "Failed to send %s notification to %s via %s",
                notification_type,
                person,
                notifier.channel,
            )
    return sent_via


def send_qualification_expiration_notification(qualification):
    """Notify a person that their qualification is about to expire."""
    context = {
        "machine": qualification.machine,
        "machine_name": qualification.machine.name,
        "qualification": qualification,
        "expires_at": qualification.expires_at,
    }
    return notify_person(qualification.person, "qualification_expiration", context)
