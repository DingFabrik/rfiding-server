from django.utils.translation import gettext_lazy as _

from base.filtering import Filter, FilterSet


class PersonFilterSet(FilterSet):
    status = Filter(
        label=_("Status"),
        choices=[
            ("active", _("Active")),
            ("inactive", _("Inactive")),
            ("all", _("All")),
        ],
        mapping={
            "inactive": {"is_active": False},
            "all": {},
            "default": {"is_active": True},
        },
        default=lambda request: request.user.default_people_filter,
    )
