from django import forms
from django.contrib.auth.models import Group
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, HTML
from crispy_forms.bootstrap import FormActions
from django.utils.translation import gettext as _

from .models import RFIDingUser, UserWidget

class ProfileForm(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            "name",
            "email",
            "language",
            "date_format",
            "time_format",
            Fieldset(
                _("Display"),
                "theme_mode",
                "theme",
                css_class="border rounded p-2 mb-3",
            ),
            Fieldset(
                _("Lists"),
                "page_length",
                "default_token_filter",
                "default_people_filter",
                "default_machines_filter",
                css_class="border rounded p-2 mb-3",
            ),
            FormActions(
                Submit("submit", _("Save"))
            )
        )
        
    class Meta:
        model = RFIDingUser
        fields = [
            "name",
            "email",
            "language",
            "date_format",
            "time_format",
            "page_length",
            "default_token_filter",
            "default_people_filter",
            "default_machines_filter",
            "theme_mode",
            "theme",
        ]

class UserForm(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            "name",
            "email",
            "is_active",
            Fieldset(
                _("Permissions"),
                "is_superuser",
                "groups",
                "user_permissions",
                css_class="border rounded p-2 mb-3",
            ),
            "last_login",
            "date_joined",
            FormActions(
                Submit("submit", _("Save")),
                HTML("""{% load i18n %}
                     {% if object and request.user.is_superuser %}
    <a class="btn btn-warning float-end me-3" href="{% url 'users:admin_change_password' object.pk %}">
        <i class="bi-key me-1"></i> {% trans 'Change Password' %}
    </a>
{% endif %}
                     {% if object and can_delete %}
            <a class="btn btn-danger float-end" href="{% url request.resolver_match.namespace|add:':delete' object.pk %}">
                <i class="bi-trash me-1"></i> {% trans 'Delete' %}
            </a>
        {% endif %}"""),
            ),
        )
    
    class Meta:
        model = RFIDingUser
        fields = [
            "name",
            "email",
            "is_superuser",
            "is_active",
            "groups",
            "user_permissions",
            "last_login",
            "date_joined",
        ]
        widgets = {
            "user_permissions": forms.SelectMultiple(attrs={"size": "17"}),
        }


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ["name", "permissions"]
        widgets = {
            "permissions": forms.SelectMultiple(attrs={"size": "17"}),
        }

class UserWidgetForm(forms.ModelForm):
    class Meta:
        model = UserWidget
        fields = ["widget", "width"]
        widgets = {
            "widget": forms.RadioSelect()
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
