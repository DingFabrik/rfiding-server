from django import forms
from django.contrib.auth.models import Group
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Field, Submit, HTML
from crispy_forms.bootstrap import FormActions
from django.utils.translation import gettext_lazy as _

from .models import RFIDingUser, UserWidget, USER_WIDGETS, WIDGET_PERMISSIONS

class ProfileForm(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            "name",
            "email",
            Fieldset(
                _("Localization"),
                "language",
                "date_format",
                "time_format",
            ),
            Fieldset(
                _("Display"),
                "theme_mode",
                "theme",
            ),
            Fieldset(
                _("Lists"),
                "page_length",
                "default_token_filter",
                "default_people_filter",
                "default_machines_filter",
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
            ),
            "last_login",
            "date_joined",
            FormActions(
                Submit("submit", _("Save")),
                HTML("""{% load i18n %}
                     <div class="flex flex-wrap gap-2">
                     {% if object and request.user.is_superuser %}
    <a class="btn btn-warning" href="{% url 'users:admin_change_password' object.pk %}">
        <i data-lucide="key" class="w-4 h-4"></i> {% trans 'Change Password' %}
    </a>
{% endif %}
                     {% if object and can_delete %}
            <a class="btn btn-error" href="{% url request.resolver_match.namespace|add:':delete' object.pk %}">
                <i data-lucide="trash-2" class="w-4 h-4"></i> {% trans 'Delete' %}
            </a>
        {% endif %}
                     </div>"""),
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

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        layout_fields = []
        if self.instance and self.instance.pk:
            del self.fields["widget"]
        else:
            self.fields["widget"].choices = [
                choice
                for choice in USER_WIDGETS
                if choice[0] not in WIDGET_PERMISSIONS
                or (user is not None and user.has_perm(WIDGET_PERMISSIONS[choice[0]]))
            ]
            layout_fields.append(Field("widget", template="widgets/widget_type_field.html"))
        layout_fields.append(Field("width", template="widgets/widget_width_field.html"))
        layout_fields.append(FormActions(Submit("submit", _("Save"))))
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Layout(*layout_fields)
