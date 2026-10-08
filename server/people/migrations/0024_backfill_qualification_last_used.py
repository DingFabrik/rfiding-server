from datetime import timedelta

from django.db import migrations
from django.db.models import Max

BATCH_SIZE = 1000


def backfill_last_used(apps, schema_editor):
    """Fill Qualification.last_used from the access logs.

    `last_used` is only recorded by access checks since it was added, so older
    qualifications look unused and would expire as soon as a machine gets an
    "unused" expiry. Their last successful access is in the access log instead.

    Compartment accesses are logged on the parent locker without saying which
    compartment was opened, so a person's last use of a locker counts for all of
    their compartment qualifications in it. That can only delay an expiry, never
    expire someone early. Logs that were anonymized (no token) or never written
    (log_enabled off) cannot be attributed.
    """
    AccessLog = apps.get_model("access_log", "AccessLog")
    Qualification = apps.get_model("people", "Qualification")

    last_access = {
        (row["token__person_id"], row["machine_id"]): row["last"]
        for row in AccessLog.objects.filter(type="enabled", token__person__isnull=False)
        .values("token__person_id", "machine_id")
        .annotate(last=Max("timestamp"))
    }
    if not last_access:
        return

    changed = []
    for qualification in Qualification.objects.select_related("machine").iterator(
        chunk_size=BATCH_SIZE
    ):
        machine = qualification.machine
        candidates = [
            last_access.get((qualification.person_id, machine_id))
            for machine_id in (machine.pk, machine.parent_id)
            if machine_id is not None
        ]
        last_used = max((c for c in candidates if c is not None), default=None)
        if last_used is None or (
            qualification.last_used is not None and qualification.last_used >= last_used
        ):
            continue
        qualification.last_used = last_used
        if qualification.expired is None:
            # Same as Qualification.compute_expires_at for a used qualification.
            days = machine.qualification_expiry_used_days
            qualification.expires_at = last_used + timedelta(days=days) if days else None
        changed.append(qualification)

    Qualification.objects.bulk_update(
        changed, ["last_used", "expires_at"], batch_size=BATCH_SIZE
    )


class Migration(migrations.Migration):

    dependencies = [
        ("access_log", "0009_accesslog_unsuccessful_reason_machine_blocked"),
        ("machines", "0040_alter_machine_log_unsuccessful"),
        ("people", "0023_alter_qualification_is_instructor_and_more"),
        ("tokens", "0016_alter_blacklistedtoken_created_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_last_used, migrations.RunPython.noop),
    ]
