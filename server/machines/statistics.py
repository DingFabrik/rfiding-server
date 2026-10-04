from access_log.models import AccessLog, LOG_TYPE_ENABLED
from access_log.statistics import compute_access_breakdown


def compute_machine_statistics(machine, days=90):
    """Access counts for `machine` over the last `days` days, by day/hour/weekday."""
    return compute_access_breakdown(
        AccessLog.objects.filter(machine=machine, type=LOG_TYPE_ENABLED), days
    )
