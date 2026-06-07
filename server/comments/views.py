from django.views.generic import CreateView
from django.utils.translation import gettext_lazy as _

from .models import Comment
from .forms import CommentForm
from base.views import TitleMixin, PermissionRequiredMixin
class CommentCreateView(TitleMixin, PermissionRequiredMixin, CreateView):
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
        return super().form_valid(form)

    def get_success_url(self):
        return self.get_content_object().get_absolute_url()