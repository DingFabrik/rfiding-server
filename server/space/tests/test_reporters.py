import io
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

from django.test import TestCase

from space.models import SpaceState
from space.reporters import (
    REPORTER_REQUEST_TIMEOUT_SECONDS,
    ConsoleReporter,
    EmailReporter,
    HttpReporter,
    SlackReporter,
)


class ConsoleReporterTests(TestCase):
    def test_report_prints_open(self):
        state = SpaceState(is_open=True)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            ConsoleReporter({}).report(state)
        self.assertIn("open", buffer.getvalue())

    def test_report_prints_closed(self):
        state = SpaceState(is_open=False)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            ConsoleReporter({}).report(state)
        self.assertIn("closed", buffer.getvalue())


class EmailReporterTests(TestCase):
    def test_report_does_not_raise(self):
        EmailReporter({}).report(SpaceState(is_open=True))


class SlackReporterTests(TestCase):
    def test_init_configures_client_channel_and_bot_name(self):
        with patch("slack_sdk.WebClient") as mock_web_client:
            reporter = SlackReporter(
                {
                    "SLACK_TOKEN": "xoxb-token",
                    "SLACK_CHANNEL": "#space",
                    "SLACK_BOT_NAME": "Space Bot",
                }
            )
        mock_web_client.assert_called_once_with(
            token="xoxb-token", timeout=REPORTER_REQUEST_TIMEOUT_SECONDS
        )
        self.assertEqual(reporter.channel, "#space")
        self.assertEqual(reporter.bot_name, "Space Bot")

    def test_report_posts_message_to_configured_channel(self):
        with patch("slack_sdk.WebClient") as mock_web_client:
            mock_client = MagicMock()
            mock_web_client.return_value = mock_client
            reporter = SlackReporter(
                {
                    "SLACK_TOKEN": "xoxb-token",
                    "SLACK_CHANNEL": "#space",
                    "SLACK_BOT_NAME": "Space Bot",
                }
            )
            reporter.report(SpaceState.objects.create(is_open=True))

        mock_client.chat_postMessage.assert_called_once()
        kwargs = mock_client.chat_postMessage.call_args.kwargs
        self.assertEqual(kwargs["channel"], "#space")
        self.assertEqual(kwargs["username"], "Space Bot")
        self.assertIn("open", kwargs["text"])


class HttpReporterTests(TestCase):
    def test_report_open_uses_open_url_when_configured(self):
        with patch("space.reporters.requests.get") as mock_get:
            HttpReporter(
                {"OPEN_URL": "https://example.com/open", "CLOSE_URL": "https://example.com/close"}
            ).report(SpaceState(is_open=True))

        mock_get.assert_called_once_with(
            "https://example.com/open", timeout=REPORTER_REQUEST_TIMEOUT_SECONDS
        )

    def test_report_closed_uses_close_url_when_configured(self):
        with patch("space.reporters.requests.get") as mock_get:
            HttpReporter(
                {"OPEN_URL": "https://example.com/open", "CLOSE_URL": "https://example.com/close"}
            ).report(SpaceState(is_open=False))

        mock_get.assert_called_once_with(
            "https://example.com/close", timeout=REPORTER_REQUEST_TIMEOUT_SECONDS
        )

    def test_report_falls_back_to_generic_url_with_state_param(self):
        with patch("space.reporters.requests.get") as mock_get:
            HttpReporter({"URL": "https://example.com/webhook"}).report(
                SpaceState(is_open=True)
            )

        mock_get.assert_called_once_with(
            "https://example.com/webhook",
            params={"state": "1"},
            timeout=REPORTER_REQUEST_TIMEOUT_SECONDS,
        )

    def test_report_falls_back_to_generic_url_closed_state(self):
        with patch("space.reporters.requests.get") as mock_get:
            HttpReporter({"URL": "https://example.com/webhook"}).report(
                SpaceState(is_open=False)
            )

        mock_get.assert_called_once_with(
            "https://example.com/webhook",
            params={"state": "0"},
            timeout=REPORTER_REQUEST_TIMEOUT_SECONDS,
        )

    def test_report_includes_extra_params(self):
        with patch("space.reporters.requests.get") as mock_get:
            HttpReporter(
                {"URL": "https://example.com/webhook", "PARAMS": {"token": "abc"}}
            ).report(SpaceState(is_open=True))

        mock_get.assert_called_once_with(
            "https://example.com/webhook",
            params={"token": "abc", "state": "1"},
            timeout=REPORTER_REQUEST_TIMEOUT_SECONDS,
        )
