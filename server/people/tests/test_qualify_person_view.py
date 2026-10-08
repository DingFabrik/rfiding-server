from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

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

    def test_excludes_lockers(self):
        locker = Machine.objects.create(name="Locker", type="lock_group")
        response = self.client.post(
            reverse("people:qualify", kwargs={"pk": self.person.pk}),
            {
                "machine_ids": [locker.pk],
                "permission_level": "if_space_open",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Qualification.objects.filter(person=self.person).exists())


    def test_form_posts_to_qualify_url(self):
        # The form is loaded into a modal on the detail page; a blank action
        # would post to the detail page instead (405).
        url = reverse("people:qualify", kwargs={"pk": self.person.pk})
        response = self.client.get(url, HTTP_HX_REQUEST="true")
        self.assertContains(response, f'<form action="{url}" method="post">')

    def test_nonexistent_person_returns_404(self):
        response = self.client.get(reverse("people:qualify", kwargs={"pk": 999999}))
        self.assertEqual(response.status_code, 404)

    def test_malformed_machine_ids_redisplay_with_error(self):
        response = self.client.post(
            reverse("people:qualify", kwargs={"pk": self.person.pk}),
            {"machine_ids": ["x", ""], "permission_level": "if_space_open"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Qualification.objects.filter(person=self.person).exists())

    def test_inactive_person_is_not_qualified(self):
        self.person.is_active = False
        self.person.save()
        response = self.client.post(
            reverse("people:qualify", kwargs={"pk": self.person.pk}),
            {"machine_ids": [self.machine.pk], "permission_level": "if_space_open"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Qualification.objects.filter(person=self.person).exists())

    def test_rejects_non_instructor_for_single_machine(self):
        outsider = Person.objects.create(name="Outsider", email="out@example.com")
        response = self.client.post(
            reverse("people:qualify", kwargs={"pk": self.person.pk}),
            {
                "machine_ids": [self.machine.pk],
                "instructed_by": outsider.pk,
                "permission_level": "if_space_open",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("instructed_by", response.context["form"].errors)
        self.assertFalse(Qualification.objects.filter(person=self.person).exists())

    def test_accepts_instructor_for_single_machine(self):
        instructor = Person.objects.create(name="Teacher", email="t@example.com")
        Qualification.objects.create(
            person=instructor, machine=self.machine, is_instructor=True
        )
        response = self.client.post(
            reverse("people:qualify", kwargs={"pk": self.person.pk}),
            {
                "machine_ids": [self.machine.pk],
                "instructed_by": instructor.pk,
                "permission_level": "if_space_open",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Qualification.objects.get(person=self.person).instructed_by, instructor
        )

    def test_rerendered_chips_match_client_labels(self):
        response = self.client.post(
            reverse("people:qualify", kwargs={"pk": self.person.pk}),
            {"machine_ids": [self.machine.pk], "permission_level": ""},
        )
        self.assertContains(
            response,
            'class="badge badge-soft badge-success gap-1 qualify-chip">m (m) <input',
        )

    def test_qualifications_list_returns_404_for_nonexistent_person(self):
        response = self.client.get(
            reverse("people:qualifications", kwargs={"pk": 999999})
        )
        self.assertEqual(response.status_code, 404)

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


    def edit_url(self):
        return reverse(
            "people:edit-qualification",
            kwargs={"pk": self.person.pk, "qualification": self.qualification.pk},
        )

    def edit_data(self, **overrides):
        data = {
            "person": self.person.pk,
            "machine": self.machine.pk,
            "permission_level": self.qualification.permission_level,
            "comment": "",
        }
        data.update(overrides)
        return data

    def test_edit_form_posts_to_edit_url(self):
        response = self.client.get(self.edit_url(), HTTP_HX_REQUEST="true")
        self.assertContains(response, f'<form action="{self.edit_url()}" method="post">')

    def test_edit_renders_notified_at_and_keeps_it_on_save(self):
        notified_at = timezone.now().replace(microsecond=0)
        self.qualification.notified_at = notified_at
        self.qualification.save()
        response = self.client.get(self.edit_url())
        self.assertContains(response, 'name="notified_at"')
        value = response.context["form"]["notified_at"].value()
        response = self.client.post(
            self.edit_url(), self.edit_data(notified_at=value)
        )
        self.assertEqual(response.status_code, 302)
        self.qualification.refresh_from_db()
        self.assertEqual(self.qualification.notified_at, notified_at)

    def test_edit_keeps_former_instructor_selected(self):
        former = Person.objects.create(name="Former", email="former@example.com")
        self.qualification.instructed_by = former
        self.qualification.save()
        response = self.client.get(self.edit_url())
        self.assertContains(response, f'<option value="{former.pk}" selected>')
        self.client.post(self.edit_url(), self.edit_data(instructed_by=former.pk))
        self.qualification.refresh_from_db()
        self.assertEqual(self.qualification.instructed_by, former)

    def test_edit_ignores_tampered_person_and_machine(self):
        other_person = Person.objects.create(name="o", email="o@example.com")
        other_machine = Machine.objects.create(
            mac_address="99:88:77:66:55:44", hostname="o", name="o"
        )
        response = self.client.post(
            self.edit_url(),
            self.edit_data(person=other_person.pk, machine=other_machine.pk),
        )
        self.assertEqual(response.status_code, 302)
        self.qualification.refresh_from_db()
        self.assertEqual(self.qualification.person, self.person)
        self.assertEqual(self.qualification.machine, self.machine)

    def test_edit_and_revoke_return_404_for_nonexistent_person(self):
        for name in ("people:edit-qualification", "people:revoke-qualification"):
            response = self.client.get(
                reverse(name, kwargs={"pk": 999999, "qualification": self.qualification.pk})
            )
            self.assertEqual(response.status_code, 404, name)

    def test_deleting_instructor_keeps_qualifications_they_instructed(self):
        instructor = Person.objects.create(name="i", email="i@example.com")
        self.qualification.instructed_by = instructor
        self.qualification.save()
        instructor.delete()
        self.qualification.refresh_from_db()
        self.assertIsNone(self.qualification.instructed_by)

    def test_revoke_page_no_link_goes_to_person(self):
        response = self.client.get(
            reverse(
                "people:revoke-qualification",
                kwargs={"pk": self.person.pk, "qualification": self.qualification.pk},
            )
        )
        self.assertContains(
            response, f'<a href="{self.person.get_absolute_url()}" class="btn">'
        )
