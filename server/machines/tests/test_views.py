import re
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from access_log.models import AccessLog, LOG_TYPE_ENABLED
from locations.models import Location
from machines.models import Machine, MachineRegistrationRequest, MachineTime
from people.models import Person, Qualification

User = get_user_model()


def time_formset_data(total=0, initial=0):
    return {
        "times-TOTAL_FORMS": str(total),
        "times-INITIAL_FORMS": str(initial),
        "times-MIN_NUM_FORMS": "0",
        "times-MAX_NUM_FORMS": "7",
    }


def minimal_machine_data(**overrides):
    data = {
        "name": "Test",
        "type": "primary",
        "state": "active",
        "chip": "esp32",
        "permission_level": "always",
        "runtimer": "0:00:00",
        "min_power": "10",
        **time_formset_data(),
    }
    data.update(overrides)
    return data


class MachineListViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.user)

    def test_default_filter_shows_active_machines(self):
        active = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:01", hostname="m1", name="active",
            state=Machine.MachineStatus.ACTIVE,
        )
        inactive = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:02", hostname="m2", name="inactive",
            state=Machine.MachineStatus.INACTIVE,
        )
        response = self.client.get(reverse("machines:list"))
        machines = list(response.context["machines"])
        self.assertIn(active, machines)
        self.assertNotIn(inactive, machines)

    def test_status_filters(self):
        Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:01", hostname="m1", name="maintenance",
            state=Machine.MachineStatus.MAINTENANCE,
        )
        response = self.client.get(reverse("machines:list"), {"filter_status": "maintenance"})
        self.assertEqual(len(response.context["machines"]), 1)

    def test_type_filter(self):
        Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:01", hostname="m1", name="lock",
            type="lock", state=Machine.MachineStatus.ACTIVE,
        )
        Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:02", hostname="m2", name="primary",
            state=Machine.MachineStatus.ACTIVE,
        )
        response = self.client.get(
            reverse("machines:list"), {"filter_status": "all", "filter_type": "lock"}
        )
        machines = list(response.context["machines"])
        self.assertEqual(len(machines), 1)
        self.assertEqual(machines[0].name, "lock")

    def test_location_filter_and_choices(self):
        location = Location.objects.create(name="Workshop")
        Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:01", hostname="m1", name="located",
            location=location, state=Machine.MachineStatus.ACTIVE,
        )
        Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:02", hostname="m2", name="unlocated",
            state=Machine.MachineStatus.ACTIVE,
        )
        response = self.client.get(
            reverse("machines:list"),
            {"filter_status": "all", "filter_location": str(location.pk)},
        )
        machines = list(response.context["machines"])
        self.assertEqual(len(machines), 1)
        self.assertEqual(machines[0].name, "located")
        options = response.context["filter_choices"]["location"]["options"]
        self.assertEqual(options[0], ("all", "All"))


class MachineDetailViewTests(TestCase):
    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m",
            needs_qualification=True,
        )
        self.user = User.objects.create_superuser(
            email="admin@example.com", password="pass"
        )

    def test_anonymous_gets_public_detail_view(self):
        response = self.client.get(reverse("machines:detail", kwargs={"pk": self.machine.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "machine_public_detail.html")

    def test_authenticated_with_permission_gets_full_detail(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("machines:detail", kwargs={"pk": self.machine.pk}))
        self.assertTemplateUsed(response, "machine_detail.html")
        self.assertTrue(response.context["can_edit"])
        self.assertTrue(response.context["can_delete"])
        self.assertIsNone(response.context["last_access"])

    def test_public_query_param_forces_public_view(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("machines:detail", kwargs={"pk": self.machine.pk}), {"public": "true"}
        )
        self.assertTemplateUsed(response, "machine_public_detail.html")

    def test_last_access_set_when_access_log_exists(self):
        self.client.force_login(self.user)
        AccessLog.objects.create(machine=self.machine, type=LOG_TYPE_ENABLED)
        response = self.client.get(reverse("machines:detail", kwargs={"pk": self.machine.pk}))
        self.assertIsNotNone(response.context["last_access"])

    def test_qualifications_context_when_needs_qualification(self):
        self.client.force_login(self.user)
        person = Person.objects.create(name="p", email="p@example.com")
        Qualification.objects.create(person=person, machine=self.machine)
        response = self.client.get(reverse("machines:detail", kwargs={"pk": self.machine.pk}))
        self.assertEqual(response.context["qualifications_count"], 1)

    def test_public_detail_shows_instructors_when_needed(self):
        person = Person.objects.create(name="Instructor", email="i@example.com")
        Qualification.objects.create(
            person=person, machine=self.machine, is_instructor=True
        )
        response = self.client.get(
            reverse("machines:detail", kwargs={"pk": self.machine.pk})
        )
        self.assertEqual(len(response.context["instructors"]), 1)

    def test_public_detail_no_instructors_when_qualification_not_needed(self):
        self.machine.needs_qualification = False
        self.machine.save()
        response = self.client.get(
            reverse("machines:detail", kwargs={"pk": self.machine.pk})
        )
        self.assertIsNone(response.context["instructors"])

    def test_locker_lists_compartments_with_last_opened(self):
        self.client.force_login(self.user)
        locker = Machine.objects.create(name="Locker", type="lock_group")
        opened = Machine.objects.create(
            name="Opened", type="compartment", parent=locker, compartment_id="1"
        )
        Machine.objects.create(
            name="Unused", type="compartment", parent=locker, compartment_id="2",
            needs_qualification=False,
        )
        AccessLog.objects.create(machine=opened, type=LOG_TYPE_ENABLED)
        AccessLog.objects.create(machine=opened, type="unsuccessful")
        response = self.client.get(reverse("machines:detail", kwargs={"pk": locker.pk}))
        compartments = {c.name: c for c in response.context["compartments"]}
        self.assertEqual(
            compartments["Opened"].last_opened,
            AccessLog.objects.get(machine=opened, type=LOG_TYPE_ENABLED).timestamp,
        )
        self.assertIsNone(compartments["Unused"].last_opened)
        self.assertContains(response, f"?parent={locker.pk}")
        self.assertContains(response, "Network")


class MachineCreateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.user)

    def test_create_machine(self):
        response = self.client.post(reverse("machines:create"), minimal_machine_data())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Machine.objects.filter(name="Test").exists())

    def test_initial_prefilled_from_registration_request(self):
        request = MachineRegistrationRequest.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="reg-host", ip_address="1.2.3.4"
        )
        response = self.client.get(reverse("machines:create"), {"request": request.pk})
        self.assertEqual(response.context["form"].initial["mac_address"], "aa:bb:cc:dd:ee:ff")
        self.assertNotIn("registration_requests", response.context)

    def test_registration_requests_listed_without_request_param(self):
        MachineRegistrationRequest.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="reg-host", ip_address="1.2.3.4"
        )
        response = self.client.get(reverse("machines:create"))
        self.assertEqual(len(response.context["registration_requests"]), 1)

    def test_creating_machine_clears_matching_registration_request(self):
        MachineRegistrationRequest.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="reg-host", ip_address="1.2.3.4"
        )
        self.client.post(
            reverse("machines:create"),
            minimal_machine_data(mac_address="aa:bb:cc:dd:ee:ff"),
        )
        self.assertFalse(MachineRegistrationRequest.objects.exists())

    def test_parent_field_limited_to_lock_groups(self):
        Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:01", hostname="m1", name="lock-group",
            type="lock_group",
        )
        Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:02", hostname="m2", name="primary",
            type="primary",
        )
        response = self.client.get(reverse("machines:create"))
        parent_qs = response.context["form"].fields["parent"].queryset
        self.assertEqual(list(parent_qs.values_list("name", flat=True)), ["lock-group"])

    def test_compartment_prefilled_from_parent_locker(self):
        locker = Machine.objects.create(name="Locker", type="lock_group")
        Machine.objects.create(
            name="a", type="compartment", parent=locker, compartment_id="3"
        )
        Machine.objects.create(
            name="b", type="compartment", parent=locker, compartment_id="top"
        )
        MachineRegistrationRequest.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="reg-host", ip_address="1.2.3.4"
        )
        response = self.client.get(reverse("machines:create"), {"parent": locker.pk})
        initial = response.context["form"].initial
        self.assertEqual(initial["type"], "compartment")
        self.assertEqual(initial["parent"], locker)
        self.assertEqual(initial["compartment_id"], "4")
        self.assertNotIn("name", initial)
        self.assertNotIn("registration_requests", response.context)

    def test_parent_param_ignored_unless_locker(self):
        primary = Machine.objects.create(name="Primary", type="primary")
        for parent in (primary.pk, "nope"):
            response = self.client.get(reverse("machines:create"), {"parent": parent})
            self.assertNotIn("parent", response.context["form"].initial)


class MachineUpdateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.user)
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="old"
        )

    def test_update_machine(self):
        response = self.client.post(
            reverse("machines:update", kwargs={"pk": self.machine.pk}),
            minimal_machine_data(name="new", mac_address="aabbccddeeff"),
        )
        self.assertEqual(response.status_code, 302)
        self.machine.refresh_from_db()
        self.assertEqual(self.machine.name, "new")

    def test_shows_can_delete(self):
        response = self.client.get(reverse("machines:update", kwargs={"pk": self.machine.pk}))
        self.assertTrue(response.context["can_delete"])


class MachineSettingsFormTests(TestCase):
    """The configure page was merged into the machine edit form."""

    def setUp(self):
        self.user = User.objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.user)
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m",
            runtimer=timedelta(minutes=5), min_power=10,
        )
        self.url = reverse("machines:update", kwargs={"pk": self.machine.pk})

    def sections_with_errors(self, response):
        return [s["key"] for s in response.context["sections"] if s["has_errors"]]

    def test_configure_redirects_to_schedule_section(self):
        response = self.client.get(
            reverse("machines:configure", kwargs={"pk": self.machine.pk})
        )
        self.assertRedirects(response, self.url + "#schedule", fetch_redirect_response=False)

    def test_get_shows_empty_formset_and_all_sections(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("formset", response.context)
        self.assertEqual(
            [s["key"] for s in response.context["sections"]],
            ["general", "access", "schedule", "session", "device", "logging"],
        )
        self.assertEqual(response.context["active_section"], "general")
        self.assertEqual(self.sections_with_errors(response), [])

    def test_key_fields_have_generate_buttons(self):
        self.machine.encryption_key = "existing"
        self.machine.save()
        response = self.client.get(self.url)
        self.assertContains(response, 'data-generate-key="encryption_key" data-target="id_encryption_key"')
        self.assertContains(response, 'data-generate-key="api_key" data-target="id_api_key"')
        self.assertContains(response, 'id="replaceKeyModal"')
        self.assertContains(response, 'value="existing"')

    def test_key_field_errors_are_shown(self):
        response = self.client.post(self.url, minimal_machine_data(api_key="x" * 65))
        self.assertEqual(self.sections_with_errors(response), ["device"])
        self.assertContains(response, 'id="error_1_id_api_key"')

    def test_saves_configuration_fields(self):
        response = self.client.post(
            self.url,
            minimal_machine_data(
                runtimer="0:10:00", min_power="20", qualification_expiry_used_days="30"
            ),
        )
        self.assertEqual(response.status_code, 302)
        self.machine.refresh_from_db()
        self.assertEqual(self.machine.min_power, 20)
        self.assertEqual(self.machine.runtimer, timedelta(minutes=10))
        self.assertEqual(self.machine.qualification_expiry_used_days, 30)

    def test_saves_new_machine_time(self):
        data = minimal_machine_data(**time_formset_data(total=1))
        data.update({
            "times-0-weekdays": ["0", "1"],
            "times-0-start_time": "08:00",
            "times-0-end_time": "18:00",
        })
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.machine.times.count(), 1)

    def test_deletes_machine_time(self):
        time = MachineTime.objects.create(
            machine=self.machine, weekdays=[0], start_time="08:00", end_time="18:00"
        )
        data = minimal_machine_data(**time_formset_data(total=1, initial=1))
        data.update({
            "times-0-id": str(time.pk),
            "times-0-weekdays": ["0"],
            "times-0-start_time": "08:00",
            "times-0-end_time": "18:00",
            "times-0-DELETE": "on",
        })
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.machine.times.count(), 0)

    def test_create_saves_machine_time(self):
        data = minimal_machine_data(**time_formset_data(total=1))
        data.update({
            "times-0-weekdays": ["5", "6"],
            "times-0-start_time": "10:00",
            "times-0-end_time": "16:00",
        })
        response = self.client.post(reverse("machines:create"), data)
        self.assertEqual(response.status_code, 302)
        machine = Machine.objects.get(name="Test")
        self.assertEqual(machine.times.count(), 1)

    def test_invalid_formset_flags_schedule_section(self):
        data = minimal_machine_data(name="changed", **time_formset_data(total=1))
        data.update({
            "times-0-weekdays": ["0"],
            "times-0-start_time": "",
            "times-0-end_time": "18:00",
        })
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["formset"].is_valid())
        self.assertEqual(self.sections_with_errors(response), ["schedule"])
        self.assertEqual(response.context["active_section"], "schedule")
        self.machine.refresh_from_db()
        self.assertEqual(self.machine.name, "m")

    def test_invalid_fields_flag_their_sections(self):
        response = self.client.post(
            self.url, minimal_machine_data(name="", min_power="", ip_address="nope")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.sections_with_errors(response), ["general", "session", "device"]
        )
        self.assertEqual(response.context["active_section"], "general")
        content = response.content.decode()
        dots = re.findall(r'data-section-dot aria-label="[^"]*"( hidden)?></span>', content)
        self.assertEqual(len(dots), 6)
        visible_dots = re.findall(r'data-section-dot aria-label="[^"]*"></span>', content)
        self.assertEqual(len(visible_dots), 3)


class MachineDeleteViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.user)

    def test_deletes_machine(self):
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m"
        )
        response = self.client.post(reverse("machines:delete", kwargs={"pk": machine.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Machine.objects.filter(pk=machine.pk).exists())


class MachinePopoverViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.user)
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m"
        )

    def test_no_access_log(self):
        response = self.client.get(
            reverse("machines:popover"), {"machine_pk": self.machine.pk}
        )
        self.assertIsNone(response.context["last_access"])

    def test_with_access_log(self):
        AccessLog.objects.create(machine=self.machine, type=LOG_TYPE_ENABLED)
        response = self.client.get(
            reverse("machines:popover"), {"machine_pk": self.machine.pk}
        )
        self.assertIsNotNone(response.context["last_access"])


class MachineStatusPartialViewTests(TestCase):
    def test_returns_manager_status(self):
        user = User.objects.create_superuser(email="admin@example.com", password="pass")
        self.client.force_login(user)
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m"
        )
        with patch(
            "machines.views.bridge.get_status",
            return_value={"state": "enabled", "verified": True},
        ) as mock_get:
            response = self.client.get(reverse("machines:status", kwargs={"pk": machine.pk}))
        self.assertEqual(response.context["status"], "enabled")
        self.assertTrue(response.context["verified"])
        mock_get.assert_called_once_with(machine.pk)

    def test_manager_not_running_shows_disconnected(self):
        user = User.objects.create_superuser(email="admin@example.com", password="pass")
        self.client.force_login(user)
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m"
        )
        response = self.client.get(reverse("machines:status", kwargs={"pk": machine.pk}))
        self.assertEqual(response.context["status"], "disconnected")


class MachineQualificationsListViewTests(TestCase):
    def test_lists_qualifications_for_machine(self):
        user = User.objects.create_superuser(email="admin@example.com", password="pass")
        self.client.force_login(user)
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m"
        )
        person = Person.objects.create(name="p", email="p@example.com")
        Qualification.objects.create(person=person, machine=machine)
        response = self.client.get(reverse("machines:qualifications", kwargs={"pk": machine.pk}))
        self.assertEqual(len(response.context["qualifications"]), 1)
        self.assertEqual(response.context["machine"], machine)


class MachineInstructorListViewTests(TestCase):
    def test_lists_only_instructors(self):
        user = User.objects.create_superuser(email="admin@example.com", password="pass")
        self.client.force_login(user)
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m"
        )
        instructor = Person.objects.create(name="i", email="i@example.com")
        other = Person.objects.create(name="o", email="o@example.com")
        Qualification.objects.create(person=instructor, machine=machine, is_instructor=True)
        Qualification.objects.create(person=other, machine=machine, is_instructor=False)
        response = self.client.get(reverse("machines:instructors", kwargs={"pk": machine.pk}))
        self.assertEqual(len(response.context["instructors"]), 1)


class MachineStatisticsViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(email="admin@example.com", password="pass")
        self.client.force_login(self.user)
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m"
        )

    def test_default_context(self):
        AccessLog.objects.create(machine=self.machine, type=LOG_TYPE_ENABLED)
        response = self.client.get(reverse("machines:statistics", kwargs={"pk": self.machine.pk}))
        self.assertEqual(response.context["selected_days"], 90)
        self.assertEqual(len(response.context["access_by_day"]), 90)
        self.assertEqual(len(response.context["access_by_hour"]), 24)
        self.assertEqual(len(response.context["access_by_weekday"]), 7)
        total = sum(d["count"] for d in response.context["access_by_day"])
        self.assertEqual(total, 1)

    def test_days_query_param(self):
        response = self.client.get(
            reverse("machines:statistics", kwargs={"pk": self.machine.pk}), {"days": 7}
        )
        self.assertEqual(response.context["selected_days"], 7)
        self.assertEqual(len(response.context["access_by_day"]), 7)

    def test_excludes_events_outside_timeframe(self):
        old_log = AccessLog.objects.create(machine=self.machine, type=LOG_TYPE_ENABLED)
        AccessLog.objects.filter(pk=old_log.pk).update(
            timestamp=timezone.now() - timedelta(days=100)
        )
        response = self.client.get(
            reverse("machines:statistics", kwargs={"pk": self.machine.pk}), {"days": 7}
        )
        total = sum(d["count"] for d in response.context["access_by_day"])
        self.assertEqual(total, 0)


class QualifyMachineViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(email="admin@example.com", password="pass")
        self.client.force_login(self.user)
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m"
        )
        self.person = Person.objects.create(name="p", email="p@example.com")

    def test_get_shows_machine_in_context(self):
        response = self.client.get(reverse("machines:qualify", kwargs={"pk": self.machine.pk}))
        self.assertEqual(response.context["machine"], self.machine)

    def test_plain_get_renders_full_page(self):
        response = self.client.get(reverse("machines:qualify", kwargs={"pk": self.machine.pk}))
        self.assertTemplateUsed(response, "base_slim.html")
        self.assertTemplateNotUsed(response, "partial_base_modal.html")

    def test_htmx_get_renders_modal_fragment(self):
        response = self.client.get(
            reverse("machines:qualify", kwargs={"pk": self.machine.pk}),
            HTTP_HX_REQUEST="true",
        )
        self.assertTemplateUsed(response, "partial_base_modal.html")
        self.assertTemplateNotUsed(response, "base_slim.html")

    def test_creates_qualification_and_redirects_to_detail(self):
        response = self.client.post(
            reverse("machines:qualify", kwargs={"pk": self.machine.pk}),
            {
                "person_ids": [self.person.pk],
                "permission_level": "if_space_open",
            },
        )
        self.assertRedirects(
            response, reverse("machines:detail", kwargs={"pk": self.machine.pk})
        )
        self.assertTrue(
            Qualification.objects.filter(machine=self.machine, person=self.person).exists()
        )

    def test_creates_multiple_qualifications_in_one_submit(self):
        other = Person.objects.create(name="q", email="q@example.com")
        response = self.client.post(
            reverse("machines:qualify", kwargs={"pk": self.machine.pk}),
            {
                "person_ids": [self.person.pk, other.pk],
                "permission_level": "if_space_open",
            },
        )
        self.assertRedirects(
            response, reverse("machines:detail", kwargs={"pk": self.machine.pk})
        )
        self.assertEqual(
            Qualification.objects.filter(machine=self.machine).count(), 2
        )

    def test_no_selection_redisplays_with_error(self):
        response = self.client.post(
            reverse("machines:qualify", kwargs={"pk": self.machine.pk}),
            {"permission_level": "if_space_open"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Qualification.objects.filter(machine=self.machine).exists())


    def test_form_posts_to_qualify_url(self):
        # The form is loaded into a modal on the detail page; a blank action
        # would post to the detail page instead (405).
        url = reverse("machines:qualify", kwargs={"pk": self.machine.pk})
        response = self.client.get(url, HTTP_HX_REQUEST="true")
        self.assertContains(response, f'<form action="{url}" method="post">')

    def test_nonexistent_machine_returns_404(self):
        response = self.client.get(reverse("machines:qualify", kwargs={"pk": 999999}))
        self.assertEqual(response.status_code, 404)

    def test_machine_without_qualification_returns_404(self):
        machine = Machine.objects.create(
            mac_address="11:22:33:44:55:66", hostname="n", name="n",
            needs_qualification=False,
        )
        url = reverse("machines:qualify", kwargs={"pk": machine.pk})
        self.assertEqual(self.client.get(url).status_code, 404)
        response = self.client.post(
            url, {"person_ids": [self.person.pk], "permission_level": "if_space_open"}
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Qualification.objects.filter(machine=machine).exists())

    def test_locker_returns_404(self):
        locker = Machine.objects.create(name="Locker", type="lock_group")
        response = self.client.get(reverse("machines:qualify", kwargs={"pk": locker.pk}))
        self.assertEqual(response.status_code, 404)

    def test_malformed_person_ids_redisplay_with_error(self):
        response = self.client.post(
            reverse("machines:qualify", kwargs={"pk": self.machine.pk}),
            {"person_ids": ["x", ""], "permission_level": "if_space_open"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Qualification.objects.filter(machine=self.machine).exists())

    def test_qualification_list_views_return_404_for_nonexistent_machine(self):
        for name in ("machines:qualifications", "machines:instructors"):
            response = self.client.get(reverse(name, kwargs={"pk": 999999}))
            self.assertEqual(response.status_code, 404, name)

class MachineRegistrationRequestDeleteViewTests(TestCase):
    def test_deletes_request_and_redirects_to_create(self):
        user = User.objects.create_superuser(email="admin@example.com", password="pass")
        self.client.force_login(user)
        request = MachineRegistrationRequest.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="h", ip_address="1.2.3.4"
        )
        response = self.client.post(
            reverse("machines:delete-request", kwargs={"pk": request.pk})
        )
        self.assertRedirects(response, reverse("machines:create"))
        self.assertFalse(MachineRegistrationRequest.objects.filter(pk=request.pk).exists())


class MachineCommentCreateViewTests(TestCase):
    def test_adds_comment_to_machine(self):
        user = User.objects.create_superuser(email="admin@example.com", password="pass")
        self.client.force_login(user)
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m"
        )
        response = self.client.post(
            reverse("machines:add-comment", kwargs={"pk": machine.pk}), {"text": "hello"}
        )
        self.assertEqual(response.status_code, 302)


class QualifyMachineViewSearchInputTests(TestCase):
    def test_person_search_input_has_name_term(self):
        user = User.objects.create_superuser(email="admin3@example.com", password="pass")
        self.client.force_login(user)
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m"
        )
        response = self.client.get(reverse("machines:qualify", kwargs={"pk": machine.pk}))
        self.assertContains(response, 'id="id_person_search" name="term"')
