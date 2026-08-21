from abc import abstractmethod
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template import engines

from .conf import PERSON_SLACK_TOKEN

logger = logging.getLogger(__name__)


class PersonNotifier:
    channel = None
    fallback_template = {}

    def __init__(self, settings=None):
        self.settings = settings or {}

    def get_template(self, notification_type):
        all_templates = getattr(settings, "PERSON_NOTIFICATION_TEMPLATES", {})
        templates = all_templates.get(notification_type, {})
        template = templates.get(self.channel)
        if template is None:
            template = all_templates.get("default", {}).get(self.channel)
        if template is None:
            template = self.fallback_template
        return template

    def render(self, template_string, context):
        return engines["django"].from_string(template_string).render(context)

    def build_context(self, person, context=None):
        data = {
            "person": person,
            "person_name": str(person),
            "person_email": person.email,
            "space_name": settings.SPACE_NAME,
        }
        if context:
            data.update(context)
        return data

    @abstractmethod
    def can_notify(self, person):
        """Whether this channel has enough contact information to reach `person`."""

    @abstractmethod
    def send(self, person, notification_type, context=None):
        """Send `notification_type` to `person`. Returns True if a message was sent."""


class EmailNotifier(PersonNotifier):
    channel = "email"
    fallback_template = {
        "subject": "Notification from {{ space_name }}",
        "body": "Hello {{ person_name }},\n\nYou have a new notification.",
    }

    def can_notify(self, person):
        return bool(person.email)

    def send(self, person, notification_type, context=None):
        if not self.can_notify(person):
            logger.debug("Skipping email notification for %s: no email address", person)
            return False
        template = self.get_template(notification_type)
        render_context = self.build_context(person, context)
        subject = self.render(template["subject"], render_context)
        body = self.render(template["body"], render_context)
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [person.email])
        logger.info("Sent %s email notification to %s", notification_type, person)
        return True


class SlackNotifier(PersonNotifier):
    channel = "slack"
    fallback_template = {
        "text": "Hello {{ person_name }}, you have a new notification.",
    }

    def __init__(self, settings=None):
        super().__init__(settings)
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from slack_sdk import WebClient

            token = self.settings.get("SLACK_TOKEN", PERSON_SLACK_TOKEN)
            self._client = WebClient(token=token)
        return self._client

    def can_notify(self, person):
        return bool(person.slack_conversation_id or person.slack_email)

    def resolve_conversation_id(self, person):
        if person.slack_conversation_id:
            return person.slack_conversation_id
        if person.slack_email:
            lookup = self.client.users_lookupByEmail(email=person.slack_email)
            user_id = lookup["user"]["id"]
            conversation = self.client.conversations_open(users=user_id)
            conversation_id = conversation["channel"]["id"]
            person.slack_conversation_id = conversation_id
            person.save(update_fields=["slack_conversation_id"])
            return conversation_id
        return None

    def send(self, person, notification_type, context=None):
        if not self.can_notify(person):
            logger.debug("Skipping slack notification for %s: no slack contact info", person)
            return False
        conversation_id = self.resolve_conversation_id(person)
        if conversation_id is None:
            return False
        template = self.get_template(notification_type)
        render_context = self.build_context(person, context)
        text = self.render(template["text"], render_context)
        self.client.chat_postMessage(channel=conversation_id, text=text)
        logger.info("Sent %s slack notification to %s", notification_type, person)
        return True
