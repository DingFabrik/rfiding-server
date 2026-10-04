from django.utils.translation import gettext_lazy as _

from base.filtering import FilterSet, MultipleChoiceFilter
from .models import LOG_TYPES, LOG_TYPE_UNSUCCESSFUL

DEFAULT_LOG_TYPES = [
    log_type for log_type, _label in LOG_TYPES if log_type != LOG_TYPE_UNSUCCESSFUL
]


class AccessLogFilterSet(FilterSet):
    action = MultipleChoiceFilter(
        field="type",
        label=_("Action"),
        choices=LOG_TYPES,
        default=DEFAULT_LOG_TYPES,
    )


class AccessLogApiFilterSet(AccessLogFilterSet):
    # API clients get every log type unless they explicitly filter.
    action = MultipleChoiceFilter(
        field="type",
        label=_("Action"),
        choices=LOG_TYPES,
    )
