from django.utils.translation import gettext_lazy as _

MACHINE_FILTER_CHOICES = (
    ("active", _("Active")),
    ("inactive", _("Inactive")),
    ("all", _("All")),
)

TOKEN_FILTER_CHOICES = (
    ("active", _("Active")),
    ("inactive", _("Inactive")),
    ("all", _("All")),
    ("archived", _("Archived")),
)

PEOPLE_FILTER_CHOICES = (
    ("active", _("Active")),
    ("inactive", _("Inactive")),
    ("all", _("All")),
)