from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from machines.models import Machine
from people.models import Person, Qualification

User = get_user_model()


class QualifyPersonViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.user)
        self.person = Person.objects.create(name="p", email="p@example.com")
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="m", name="m"
        )

    def test_get_shows_person_in_context(self):
        response = self.client.get(reverse("people:qualify", kwargs={"pk": self.person.pk}))
        self.assertEqual(response.context["person"], self.person)

    def test_plain_get_renders_full_page(self):
        response = self.client.get(reverse("people:qualify", kwargs={"pk": self.person.pk}))
        self.assertTemplateUsed(response, "base_slim.html")
        self.assertTemplateNotUsed(response, "partial_base_modal.html")

    def test_htmx_get_renders_modal_fragment(self):
        response = self.client.get(
            reverse("people:qualify", kwargs={"pk": self.person.pk}),
            HTTP_HX_REQUEST="true",
        )
        self.assertTemplateUsed(response, "partial_base_modal.html")
        self.assertTemplateNotUsed(response, "base_slim.html")

    def test_creates_multiple_qualifications_in_one_submit(self):
        other_machine = Machine.objects.create(
            mac_address="11:22:33:44:55:66", hostname="m2", name="m2"
        )
        response = self.client.post(
            reverse("people:qualify", kwargs={"pk": self.person.pk}),
            {
                "machine_ids": [self.machine.pk, other_machine.pk],
                "permission_level": "if_space_open",
            },
        )
        self.assertRedirects(
            response, reverse("people:detail", kwargs={"pk": self.person.pk})
        )
        self.assertEqual(Qualification.objects.filter(person=self.person).count(), 2)

    def test_no_selection_redisplays_with_error_and_preserves_previous_selection(self):
        response = self.client.post(
            reverse("people:qualify", kwargs={"pk": self.person.pk}),
            {
                "machine_ids": [],
                "permission_level": "if_space_open",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Qualification.objects.filter(person=self.person).exists())

    def test_excludes_inactive_machines(self):
        inactive = Machine.objects.create(
            mac_address="11:22:33:44:55:66",
            hostname="m2",
            name="m2",
            state=Machine.MachineStatus.INACTIVE,
        )
        response = self.client.post(
            reverse("people:qualify", kwargs={"pk": self.person.pk}),
            {
                "machine_ids": [inactive.pk],
                "permission_level": "if_space_open",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Qualification.objects.filter(person=self.person).exists())


class RevokeAndEditQualificationViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            email="admin2@example.com", password="pass"
        )
        self.client.force_login(self.user)
        self.person = Person.objects.create(name="p2", email="p2@example.com")
        self.machine = Machine.objects.create(
            mac_address="11:22:33:44:55:66", hostname="m2", name="m2"
        )
        self.qualification = Qualification.objects.create(
            person=self.person, machine=self.machine
        )

    def test_revoke_deletes_qualification_and_redirects(self):
        response = self.client.post(
            reverse(
                "people:revoke-qualification",
                kwargs={"pk": self.person.pk, "qualification": self.qualification.pk},
            )
        )
        self.assertRedirects(
            response, reverse("people:detail", kwargs={"pk": self.person.pk})
        )
        self.assertFalse(
            Qualification.objects.filter(pk=self.qualification.pk).exists()
        )

    def test_edit_qualification_get_renders(self):
        response = self.client.get(
            reverse(
                "people:edit-qualification",
                kwargs={"pk": self.person.pk, "qualification": self.qualification.pk},
            )
        )
        self.assertEqual(response.status_code, 200)

    def test_edit_qualification_htmx_get_renders_modal_fragment(self):
        response = self.client.get(
            reverse(
                "people:edit-qualification",
                kwargs={"pk": self.person.pk, "qualification": self.qualification.pk},
            ),
            HTTP_HX_REQUEST="true",
        )
        self.assertTemplateUsed(response, "partial_base_modal.html")
        self.assertTemplateNotUsed(response, "base_slim.html")
