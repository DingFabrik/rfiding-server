from django.utils.translation import gettext_lazy as _

from base.filtering import Filter, FilterSet
from .models import LOG_TYPES


class AccessLogFilterSet(FilterSet):
    action = Filter(
        field="type",
        label=_("Action"),
        choices=[("all", _("All"))] + list(LOG_TYPES),
        default="all",
    )
