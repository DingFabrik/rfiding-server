import logging

logger = logging.getLogger(__name__)


def send_qualification_expiration_notification(qualification):
    """Generic stub for notifying a person their qualification is about to expire.

    Later this should dispatch through a real channel (email, Slack, ...).
    """
    logger.info(
        "Qualification expiration notice: %s on %s expires at %s",
        qualification.person,
        qualification.machine,
        qualification.expires_at,
    )
