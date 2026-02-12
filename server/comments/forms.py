from django import forms
from django.utils.translation import gettext as _

from comments.models import Comment

class CommentForm(forms.ModelForm):
    text = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), label=_("Comment"))
    class Meta:
        model = Comment
        fields = ["text"]