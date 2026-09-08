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
    if not pairs:
        return []

    with transaction.atomic():
        Qualification.objects.bulk_create(
            [
                Qualification(person=person_obj, machine=machine_obj, **fields)
                for person_obj, machine_obj in pairs
            ],
            ignore_conflicts=True,
        )

    return list(
        Qualification.objects.filter(
            person__in=[person_obj for person_obj, _ in pairs],
            machine__in=[machine_obj for _, machine_obj in pairs],
        )
    )
