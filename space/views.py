from django.views.generic import TemplateView
from django.utils.translation import gettext as _
from datetime import datetime, timedelta, timezone

from .models import SpaceState
from rfiding import settings

class ShowSpaceStatus(TemplateView):
    template_name = "status.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["state"] = SpaceState.objects.first()
        context["space_name"] = settings.SPACE_NAME
        if hasattr(settings, "SPACE_CONTACT"):
            context["space_contact"] = settings.SPACE_CONTACT
        if context["state"] is not None:
            context["state_text"] = (
                _("open") if context["state"].is_open else _("closed")
            )

            timestamp = context["state"].updated
            if datetime.now(tz=timezone.utc) - timestamp > timedelta(hours=12):
                context["warning"] = _("Space status might not be accurate anymore! Consider contacting the space.")
        return context
