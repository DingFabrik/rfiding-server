from abc import ABC, abstractmethod
from slack_sdk import WebClient
import logging

logger = logging.getLogger(__name__)

class StateReporter():
    @abstractmethod
    def report(self, state):
        pass

class ConsoleReporter(StateReporter):
    def report(self, state):
        logger.info(f"Reporting new state to console: {'open' if state.is_open else 'closed'}")


class SlackReporter(StateReporter):

    def __init__(self, settings):
        self.client = WebClient(token=settings["SLACK_TOKEN"])
        self.channel = settings["SLACK_CHANNEL"]
        self.bot_name = settings["SLACK_BOT_NAME"]

    def report(self, state):
        logger.info(f"Reporting new state to slack: {'open' if state.is_open else 'closed'}")
        self.client.chat_postMessage(
            channel=self.channel, 
            text=f"Space is {'open' if state.is_open else 'closed'}", 
            username=self.bot_name
        )


class EmailReporter(StateReporter):
    def report(self, state):
        logger.info(f"Reporting new state to email: {'open' if state.is_open else 'closed'}")


class HttpReporter(StateReporter):
    def report(self, state):
        logger.info(f"Reporting new state to http: {'open' if state.is_open else 'closed'}")
