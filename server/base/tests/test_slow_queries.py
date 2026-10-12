from django.db import connection
from django.db.backends.signals import connection_created
from django.test import TestCase, override_settings

from base.slow_queries import enable_slow_query_logging, log_slow_queries
from people.models import Person


class SlowQueryLoggingTests(TestCase):
    def tearDown(self):
        connection_created.disconnect(dispatch_uid="slow_query_logging")
        if log_slow_queries in connection.execute_wrappers:
            connection.execute_wrappers.remove(log_slow_queries)

    @override_settings(SLOW_QUERY_THRESHOLD_MS=0)
    def test_logs_slow_queries(self):
        enable_slow_query_logging()
        with self.assertLogs("rfiding.slow_queries", "WARNING") as logs:
            Person.objects.filter(name="secret-name").count()
        self.assertEqual(len(logs.output), 1)
        self.assertIn("Slow query", logs.output[0])
        self.assertIn("people_person", logs.output[0])
        # Parameters may contain secrets.
        self.assertNotIn("secret-name", logs.output[0])

    @override_settings(SLOW_QUERY_THRESHOLD_MS=10_000)
    def test_ignores_fast_queries(self):
        enable_slow_query_logging()
        with self.assertNoLogs("rfiding.slow_queries"):
            Person.objects.count()

    @override_settings(SLOW_QUERY_THRESHOLD_MS=None)
    def test_disabled_without_threshold(self):
        enable_slow_query_logging()
        self.assertNotIn(log_slow_queries, connection.execute_wrappers)

    @override_settings(SLOW_QUERY_THRESHOLD_MS=0)
    def test_installs_once(self):
        enable_slow_query_logging()
        enable_slow_query_logging()
        self.assertEqual(connection.execute_wrappers.count(log_slow_queries), 1)
