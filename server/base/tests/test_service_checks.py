import io
import json
import os
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from base import build, checks
from machines.esphome import bridge

CURRENT = "current00000"


def ids(messages):
    return [message.id for message in messages]


class BuildVersionTests(SimpleTestCase):
    def test_version_is_stable(self):
        self.assertEqual(build.current_version(), build.current_version())
        self.assertEqual(len(build.current_version()), 12)

    def test_build_id_from_environment(self):
        with patch.dict(os.environ, {"RFIDING_BUILD_ID": "abc"}):
            self.assertEqual(build.current_version(), "abc")

    def test_running_version_is_fixed_at_startup(self):
        version = build.running_version()
        with patch.dict(os.environ, {"RFIDING_BUILD_ID": "changed"}):
            self.assertEqual(build.running_version(), version)


class VersionViewTests(TestCase):
    def test_requires_token(self):
        self.assertEqual(self.client.get(reverse("health-version")).status_code, 404)
        response = self.client.get(reverse("health-version"), headers={"X-Health-Token": "wrong"})
        self.assertEqual(response.status_code, 404)

    def test_reports_running_version(self):
        response = self.client.get(
            reverse("health-version"), headers={"X-Health-Token": build.health_token()}
        )
        self.assertEqual(response.json(), {"version": build.running_version()})


@patch("base.checks.build.current_version", return_value=CURRENT)
class WebVersionCheckTests(SimpleTestCase):
    def respond(self, version):
        return MagicMock(
            __enter__=lambda self: io.BytesIO(json.dumps({"version": version}).encode()),
            __exit__=lambda *args: False,
        )

    def test_not_configured(self, current):
        self.assertEqual(ids(checks.check_web_version(None)), ["services.W001"])

    @override_settings(HEALTH_CHECK_URL="https://rfiding.example.com")
    def test_up_to_date(self, current):
        with patch("base.checks.urllib.request.urlopen", return_value=self.respond(CURRENT)) as urlopen:
            self.assertEqual(checks.check_web_version(None), [])
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://rfiding.example.com/health/version")
        self.assertEqual(request.get_header("X-health-token"), build.health_token())

    @override_settings(HEALTH_CHECK_URL="https://rfiding.example.com")
    def test_outdated(self, current):
        with patch("base.checks.urllib.request.urlopen", return_value=self.respond("old")):
            self.assertEqual(ids(checks.check_web_version(None)), ["services.E002"])

    @override_settings(HEALTH_CHECK_URL="https://rfiding.example.com")
    def test_not_running(self, current):
        with patch("base.checks.urllib.request.urlopen", side_effect=OSError("Connection refused")):
            self.assertEqual(ids(checks.check_web_version(None)), ["services.E001"])


@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
@patch("base.checks.build.current_version", return_value=CURRENT)
@patch("rfiding.celery.app.connection_for_write")
class CeleryVersionCheckTests(SimpleTestCase):
    def inspect(self, replies):
        return patch(
            "rfiding.celery.app.control.inspect",
            return_value=MagicMock(rfiding_version=MagicMock(return_value=replies)),
        )

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_skipped_without_workers(self, connection, current):
        self.assertEqual(checks.check_celery_version(None), [])
        connection.assert_not_called()

    def test_up_to_date(self, connection, current):
        with self.inspect({"celery@a": {"version": CURRENT}, "celery@b": {"version": CURRENT}}):
            self.assertEqual(checks.check_celery_version(None), [])

    def test_outdated_workers(self, connection, current):
        replies = {
            "celery@a": {"version": CURRENT},
            "celery@b": {"version": "old"},
            "celery@c": {"error": "No such inspect command"},
        }
        with self.inspect(replies):
            messages = checks.check_celery_version(None)
        self.assertEqual(ids(messages), ["services.E005", "services.E005"])
        self.assertIn("celery@b", messages[0].msg)
        self.assertIn("celery@c", messages[1].msg)

    def test_no_worker(self, connection, current):
        with self.inspect(None):
            self.assertEqual(ids(checks.check_celery_version(None)), ["services.E004"])

    def test_broker_down(self, connection, current):
        connection.return_value.__enter__.return_value.ensure_connection.side_effect = OSError("refused")
        self.assertEqual(ids(checks.check_celery_version(None)), ["services.E003"])


@override_settings(ENABLE_CLIENT_API=True)
@patch("base.checks.build.current_version", return_value=CURRENT)
class MachineManagerVersionCheckTests(SimpleTestCase):
    def manager(self, **kwargs):
        return patch("machines.esphome.bridge.aget_version", **kwargs)

    @override_settings(ENABLE_CLIENT_API=False)
    def test_skipped_when_client_api_disabled(self, current):
        self.assertEqual(checks.check_machine_manager_version(None), [])

    def test_up_to_date(self, current):
        with self.manager(return_value=CURRENT):
            self.assertEqual(checks.check_machine_manager_version(None), [])

    def test_outdated(self, current):
        with self.manager(return_value="old"):
            self.assertEqual(ids(checks.check_machine_manager_version(None)), ["services.E007"])

    def test_too_old_to_report_a_version(self, current):
        with self.manager(side_effect=bridge.CommandFailed("Unknown request manager.version")):
            self.assertEqual(ids(checks.check_machine_manager_version(None)), ["services.E007"])

    def test_not_running(self, current):
        with self.manager(side_effect=bridge.ManagerUnavailable("did not answer")):
            self.assertEqual(ids(checks.check_machine_manager_version(None)), ["services.E006"])
