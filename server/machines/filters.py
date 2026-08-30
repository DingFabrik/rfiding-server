from django.utils.translation import gettext_lazy as _

from base.filtering import Filter, FilterSet
from locations.models import Location
from .models import Machine


def _location_choices():
    return [(str(location.pk), location.name) for location in Location.objects.all()]


class MachineFilterSet(FilterSet):
    status = Filter(
        label=_("Status"),
        choices=[
            ("active", _("Active")),
            ("inactive", _("Inactive")),
            ("maintenance", _("Maintenance")),
            ("all", _("All")),
        ],
        mapping={
            "inactive": {"state": Machine.MachineStatus.INACTIVE},
            "maintenance": {"state": Machine.MachineStatus.MAINTENANCE},
            "all": {},
            "default": {"state": Machine.MachineStatus.ACTIVE},
        },
        default=lambda request: request.user.default_machines_filter,
    )
    type = Filter(
        label=_("Type"),
        choices=[
            ("all", _("All")),
            ("primary", _("Primary")),
            ("secondary", _("Secondary")),
            ("lock", _("Lock")),
            ("lock_group", _("Lock Group")),
            ("compartment", _("Compartment")),
        ],
        default="all",
    )
    location = Filter(
        label=_("Location"),
        choices=lambda: [("all", _("All"))] + _location_choices(),
        default="all",
    )
