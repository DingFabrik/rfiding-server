from django.utils.translation import gettext_lazy as _

ACCESS_CONTROL_MODULES = {
    (0, _("None")),
    (1, _("RFID Reader")),
}

STATUS_DISPLAY_MODULES = {
    (0, _("None")),
    (1, _("Onboard LED")),
    (2, _("Double LEDs")),
    (3, _("Red/Green LED")),
    (4, _("Single RGB LED")),
    (5, _("RGB Ring LED")),
}

ACTOR_MODULES = {
    (0, _("None")),
    (1, _("Relay")),
    (2, _("Relay with power meter")),
    (3, _("Lock")),
}