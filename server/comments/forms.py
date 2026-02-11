from django import forms
from django.utils.translation import gettext as _

from comments.models import Comment

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["text"]