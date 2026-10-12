"""Logs slow database queries in processes Silk doesn't see: Celery workers and
the machine manager.

Only the SQL is logged, not its parameters: those can contain secrets such as
session keys and tokens.
"""

import logging
import time

from celery import current_task
from django.conf import settings
from django.db import connections
from django.db.backends.signals import connection_created

logger = logging.getLogger("rfiding.slow_queries")

MAX_LOGGED_SQL_LENGTH = 2000


def log_slow_queries(execute, sql, params, many, context):
    start = time.perf_counter()
    try:
        return execute(sql, params, many, context)
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        if duration_ms >= settings.SLOW_QUERY_THRESHOLD_MS:
            task = f" in task {current_task.name}" if current_task else ""
            logger.warning(
                "Slow query (%d ms)%s: %s",
                duration_ms,
                task,
                sql[:MAX_LOGGED_SQL_LENGTH],
            )


def install(connection, **kwargs):
    if log_slow_queries not in connection.execute_wrappers:
        connection.execute_wrappers.append(log_slow_queries)


def enable_slow_query_logging():
    """Logs queries taking at least SLOW_QUERY_THRESHOLD_MS on every connection
    of this process, including ones opened later by other threads."""
    if settings.SLOW_QUERY_THRESHOLD_MS is None:
        return
    connection_created.connect(install, dispatch_uid="slow_query_logging")
    for connection in connections.all(initialized_only=True):
        install(connection)
