import os

from celery import Celery, signals
from celery.worker.control import inspect_command

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rfiding.settings")

app = Celery("rfiding")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@signals.worker_init.connect
def enable_slow_query_logging(**kwargs):
    # Before the pool forks, so every worker process inherits it.
    from base.slow_queries import enable_slow_query_logging

    enable_slow_query_logging()


@inspect_command()
def rfiding_version(state):
    from base.build import running_version

    return {"version": running_version()}
