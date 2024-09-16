from django.views.generic import TemplateView
from django.utils.translation import gettext as _

from .models import SpaceState


class ShowSpaceStatus(TemplateView):
    template_name = "status.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["state"] = SpaceState.objects.first()
        if context["state"] is not None:
            context["status_text"] = (
                _("open") if context["state"].is_open else _("closed")
            )
        return context
