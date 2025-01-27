from abc import abstractmethod
from django.conf import settings
from django.utils.translation import gettext as _
from django.utils import timezone, formats
import logging

import requests

logger = logging.getLogger(__name__)


space_name = settings.SPACE_NAME
class StateReporter:

    def __init__(self, settings):
        self.settings = settings

    @abstractmethod
    def report(self, state):
        pass


class ConsoleReporter(StateReporter):
    
    def report(self, state):
        logger.debug(
            f"Reporting new state to console: {'open' if state.is_open else 'closed'}"
        )
        print("Space is", "open" if state.is_open else "closed")


class SlackReporter(StateReporter):
    def __init__(self, settings):
        from slack_sdk import WebClient
        self.client = WebClient(token=settings["SLACK_TOKEN"])
        if "SLACK_CHANNEL" in settings:
            self.channel = settings["SLACK_CHANNEL"]
        if "SLACK_BOT_NAME" in settings:
            self.bot_name = settings["SLACK_BOT_NAME"]

    def report(self, state):
        logger.debug(
            f"Reporting new state to slack: {'open' if state.is_open else 'closed'}"
        )
        self.client.chat_postMessage(
            channel=self.channel,
            text=_("{} is now {}").format(space_name, _("open") if state.is_open else _("closed")),
            attachments=[
                {
                    "color": "#9BE564" if state.is_open else "#F95738",
                "blocks": [
                {
                    "type": "section",
                    "text": {
                    "type": "mrkdwn",
                    "text": _("{} is now *{}*").format(space_name, _("open") if state.is_open else _("closed"))
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "plain_text",
                            "text": formats.date_format(timezone.localtime(state.created), "SHORT_DATETIME_FORMAT")
                        }
                    ]
                }
                ]
            }],
            username=self.bot_name,
            icon_emoji=":door:"
        )


class EmailReporter(StateReporter):
    def report(self, state):
        logger.debug(
            f"Reporting new state to email: {'open' if state.is_open else 'closed'}"
        )


class HttpReporter(StateReporter):
    def report(self, state):
        logger.debug(
            f"Reporting new state to http: {'open' if state.is_open else 'closed'}"
        )
        params = self.settings.get("PARAMS", {})
        params["state"] = "1" if state.is_open else "0"
        requests.get(self.settings["URL"], params=params)
