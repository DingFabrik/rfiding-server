from django.views.generic import CreateView
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render

from .models import Comment
from .forms import CommentForm
from base.views import TitleMixin, PermissionRequiredMixin, PartialMixin
class CommentCreateView(TitleMixin, PartialMixin, PermissionRequiredMixin, CreateView):
    permission_required = "machines.view_machine"

    model = Comment
    template_name = "comment_form.html"
    form_class = CommentForm

    content_model = None
    content_object = None

    def get_title(self):
        return _(f"Add Comment to {self.get_content_object().name}")

    def get_content_object(self):
        if self.content_object is None:
            self.content_object = self.content_model.objects.get(pk=self.kwargs["pk"])
        return self.content_object

    def form_valid(self, form):
        form.instance.content_object = self.get_content_object()
        form.instance.author = self.request.user
        response = super().form_valid(form)
        if self.is_partial:
            return self.render_tab_pane()
        return response

    def form_invalid(self, form):
        if self.is_partial:
            return self.render_tab_pane(comment_form=form)
        return super().form_invalid(form)

    def render_tab_pane(self, comment_form=None):
        context = {
            "object": self.get_content_object(),
            "comment_form": comment_form or CommentForm(),
            "comment_url": self.request.resolver_match.view_name,
        }
        return render(self.request, "comment_tab_pane.html", context)

    def get_success_url(self):
        return self.get_content_object().get_absolute_url()