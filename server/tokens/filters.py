from django.utils.translation import gettext_lazy as _

from base.filtering import Filter, FilterSet
from .models import TokenType


def _token_type_choices():
    return [(str(pk), name) for pk, name in TokenType.objects.values_list("pk", "name")]


class TokenFilterSet(FilterSet):
    status = Filter(
        label=_("Status"),
        choices=[
            ("active", _("Active")),
            ("inactive", _("Inactive")),
            ("all", _("All")),
            ("archived", _("Archived")),
        ],
        mapping={
            "inactive": {"is_active": False, "archived__isnull": True},
            "archived": {"archived__isnull": False},
            "all": {"archived__isnull": True},
            "default": {"is_active": True, "archived__isnull": True},
        },
        default=lambda request: request.user.default_token_filter,
    )
    type = Filter(
        label=_("Type"),
        choices=lambda: [("all", _("All"))] + _token_type_choices(),
        default="all",
    )
