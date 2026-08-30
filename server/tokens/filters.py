from django.utils.translation import gettext_lazy as _

from base.filtering import Filter, FilterSet
from .models import TokenType


def _token_type_choices():
    return [(str(token_type.pk), token_type.name) for token_type in TokenType.objects.all()]


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
