"""Sign-in for people (members) to their own self-service page.

People are not Django users, so they are tracked in the session separately from
`request.user`. A staff user can be signed in as both at the same time.
"""

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import formats, timezone, translation
from django.utils.translation import gettext as _, ngettext

from .conf import (
    PERSON_LOGIN_CODE_VALID_MINUTES,
    PERSON_PAGE_EXPIRY_WARNING_DAYS,
    PERSON_SESSION_VALID_HOURS,
)
from .models import Person

logger = logging.getLogger(__name__)

SESSION_KEY = "self_service_person"
PENDING_EMAIL_SESSION_KEY = "self_service_pending_email"


def login_person(request, person):
    request.session.cycle_key()
    expires = timezone.now() + timedelta(hours=PERSON_SESSION_VALID_HOURS)
    request.session[SESSION_KEY] = {"id": person.pk, "expires": expires.timestamp()}
    request.session.pop(PENDING_EMAIL_SESSION_KEY, None)


def logout_person(request):
    request.session.pop(SESSION_KEY, None)


def get_logged_in_person(request):
    data = request.session.get(SESSION_KEY)
    if not data:
        return None
    if data.get("expires", 0) <= timezone.now().timestamp():
        logout_person(request)
        return None
    person = Person.objects.filter(pk=data.get("id"), is_active=True).first()
    if person is None:
        logout_person(request)
    return person


def send_login_code(request, person):
    """E-mail `person` a fresh login code and a link to their page."""
    code = person.generate_login_code()
    context = {
        "person": person,
        "code": code,
        "link": request.build_absolute_uri(person.get_detail_url()),
        "login_url": request.build_absolute_uri(reverse("people:me-verify")),
        "valid_minutes": PERSON_LOGIN_CODE_VALID_MINUTES,
        "space_name": settings.SPACE_NAME,
    }
    with translation.override(person.language):
        subject = render_to_string("emails/login_code_subject.txt", context).strip()
        body = render_to_string("emails/login_code_body.txt", context)
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [person.email])
    logger.info("Sent self-service login code to %s", person)


@dataclass
class QualificationRow:
    qualification: object
    # "expiring", "expired" or "valid"
    status: str
    status_label: str
    expires: object
    rule: str

    @property
    def machine(self):
        return self.qualification.machine

    @property
    def location(self):
        machine = self.machine
        return machine.location or (machine.parent.location if machine.parent else None)


def _expiry_rule(qualification):
    machine = qualification.machine
    if qualification.expired is not None:
        if qualification.last_used is None:
            days = machine.qualification_expiry_unused_days
            if days:
                return ngettext(
                    "Not used within %(days)d day of training",
                    "Not used within %(days)d days of training",
                    days,
                ) % {"days": days}
            return _("Not used after training")
        days = machine.qualification_expiry_used_days
        if days:
            return ngettext(
                "Not used within %(days)d day",
                "Not used within %(days)d days",
                days,
            ) % {"days": days}
        return ""
    if qualification.expires_at is None:
        return ""
    if qualification.last_used is not None:
        days = machine.qualification_expiry_used_days
        if not days:
            return ""
        return ngettext(
            "%(days)d day after last use (%(date)s)",
            "%(days)d days after last use (%(date)s)",
            days,
        ) % {
            "days": days,
            "date": formats.date_format(timezone.localtime(qualification.last_used)),
        }
    days = machine.qualification_expiry_unused_days
    if not days:
        return ""
    return ngettext(
        "If not used within %(days)d day of training",
        "If not used within %(days)d days of training",
        days,
    ) % {"days": days}


def build_qualification_rows(person, now=None):
    """The person's qualifications, the ones needing attention first: expiring
    soon, then expired, then valid ones."""
    now = now or timezone.now()
    warn_after = now + timedelta(days=PERSON_PAGE_EXPIRY_WARNING_DAYS)
    rows = []
    qualifications = person.qualifications.select_related(
        "machine", "machine__location", "machine__parent__location", "instructed_by"
    )
    for qualification in qualifications:
        expires_at = qualification.expires_at
        if qualification.expired is not None:
            status, label = "expired", _("Expired")
            expires = expires_at or qualification.expired
        elif expires_at is not None and expires_at <= warn_after:
            days = max((timezone.localdate(expires_at) - timezone.localdate(now)).days, 0)
            status = "expiring"
            label = ngettext(
                "Expires in %(days)d day", "Expires in %(days)d days", days
            ) % {"days": days}
            expires = expires_at
        else:
            status, label, expires = "valid", _("Valid"), expires_at
        rows.append(
            QualificationRow(qualification, status, label, expires, _expiry_rule(qualification))
        )

    order = {"expiring": 0, "expired": 1, "valid": 2}
    far_future = now + timedelta(days=365 * 1000)

    def sort_key(row):
        expires = row.expires or far_future
        # Most recently expired first; otherwise the soonest expiry first.
        timestamp = -expires.timestamp() if row.status == "expired" else expires.timestamp()
        return (order[row.status], timestamp, row.machine.name.lower())

    rows.sort(key=sort_key)
    return rows
