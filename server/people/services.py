from django.db import transaction

from .models import Qualification


def bulk_qualify(*, machine=None, people=None, person=None, machines=None, **fields):
    """Create a Qualification for each (person, machine) pair.

    Exactly one of (`machine` + `people`) or (`person` + `machines`) must be
    given - the fixed side plus the iterable of the other side selected in
    the multi-select qualify form. `**fields` (permission_level, comment, ...)
    is applied to every Qualification created. Existing pairs are left alone
    (`get_or_create`) rather than raising the model's unique constraint - a
    stale/duplicate selection is silently skipped.
    """
    if people is not None:
        pairs = [(person_obj, machine) for person_obj in people]
    else:
        pairs = [(person, machine_obj) for machine_obj in machines]

    # get_or_create rather than bulk_create so auditlog's save signals fire.
    qualifications = []
    with transaction.atomic():
        for person_obj, machine_obj in pairs:
            qualification, _created = Qualification.objects.get_or_create(
                person=person_obj, machine=machine_obj, defaults=fields
            )
            qualifications.append(qualification)
    return qualifications
