from django.utils.translation import gettext_lazy as _

MACHINE_FILTER_CHOICES = {
    "status": {
        "label": _("Status"),
        "options": [
            ("active", _("Active")),
            ("inactive", _("Inactive")),
            ("maintenance", _("Maintenance")),
            ("all", _("All"))
        ]
    },
    "type": {
        "label": _("Type"),
        "options": [
            ("all", _("All")),
            ("primary", _("Primary")),
            ("secondary", _("Secondary")),
            ("lock", _("Lock")),
            ("lock_group", _("Lock Group")),
            ("compartment", _("Compartment")),
        ]
    },
    "location": {
        "label": _("Location"),
        "options": [
            ("all", _("All")),
        ]
    }
}

TOKEN_FILTER_CHOICES = {
    "status": {
        "label": _("Status"),
        "options": [
            ("active", _("Active")),
            ("inactive", _("Inactive")),
            ("all", _("All")),
            ("archived", _("Archived")),
        ]
    },
    "type": {
        "label": _("Type"),
        "options": [
            ("all", _("All")),
        ]
    }
}

PEOPLE_FILTER_CHOICES = {
    "status": {
        "label": _("Status"),
        "options": [
            ("active", _("Active")),
            ("inactive", _("Inactive")),
            ("all", _("All")),
        ]
    }
}