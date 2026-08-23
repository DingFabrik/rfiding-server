from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from access_log.models import AccessLog, LOG_TYPE_ENABLED
from locations.models import Location
from machines.models import Machine, MachineRegistrationRequest
from people.models import Person, Qualification

User = get_user_model()


def minimal_machine_data(**overrides):
    data = {"name": "Test", "type": "primary", "state": "active", "chip": "esp32"}
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


class MachineConfigureViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.user)
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m",
            runtimer=timedelta(minutes=5), min_power=10,
        )
        self.url = reverse("machines:configure", kwargs={"pk": self.machine.pk})

    def formset_management_data(self, total=0, initial=0):
        return {
            "times-TOTAL_FORMS": str(total),
            "times-INITIAL_FORMS": str(initial),
            "times-MIN_NUM_FORMS": "0",
            "times-MAX_NUM_FORMS": "7",
        }

    def test_get_shows_empty_formset(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("formset", response.context)

    def test_valid_form_and_formset_saves(self):
        data = {
            "runtimer": "0:10:00",
            "min_power": "20",
            "qualification_expiry_unused_days": "",
            "qualification_expiry_used_days": "",
            **self.formset_management_data(),
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.machine.refresh_from_db()
        self.assertEqual(self.machine.min_power, 20)

    def test_valid_form_saves_new_machine_time(self):
        data = {
            "runtimer": "0:10:00",
            "min_power": "20",
            "qualification_expiry_unused_days": "",
            "qualification_expiry_used_days": "",
            **self.formset_management_data(total=1),
            "times-0-weekdays": ["0", "1"],
            "times-0-start_time": "08:00",
            "times-0-end_time": "18:00",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.machine.times.count(), 1)

    def test_invalid_formset_rerenders_form(self):
        data = {
            "runtimer": "0:10:00",
            "min_power": "20",
            "qualification_expiry_unused_days": "",
            "qualification_expiry_used_days": "",
            **self.formset_management_data(total=1),
            "times-0-weekdays": ["0"],
            "times-0-start_time": "",
            "times-0-end_time": "18:00",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["formset"].is_valid())


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
    def test_returns_socket_status(self):
        user = User.objects.create_superuser(email="admin@example.com", password="pass")
        self.client.force_login(user)
        machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m"
        )
        with patch("machines.views.get_socket_data", return_value="enabled") as mock_get:
            response = self.client.get(reverse("machines:status", kwargs={"pk": machine.pk}))
        self.assertEqual(response.context["status"], "enabled")
        mock_get.assert_called_once_with(machine.pk, "status")


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

    def test_creates_qualification_and_redirects_to_detail(self):
        response = self.client.post(
            reverse("machines:qualify", kwargs={"pk": self.machine.pk}),
            {
                "machine": self.machine.pk,
                "person": self.person.pk,
                "permission_level": "if_space_open",
            },
        )
        self.assertRedirects(
            response, reverse("machines:detail", kwargs={"pk": self.machine.pk})
        )
        self.assertTrue(
            Qualification.objects.filter(machine=self.machine, person=self.person).exists()
        )


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
