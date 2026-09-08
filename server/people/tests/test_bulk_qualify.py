from django.test import TestCase

from machines.models import Machine
from people.forms import BulkQualifyForm
from people.models import Person, Qualification
from people.services import bulk_qualify


class BulkQualifyFormTests(TestCase):
    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        self.instructor = Person.objects.create(name="Instructor", email="i@example.com")
        self.other_person = Person.objects.create(name="Other", email="o@example.com")
        Qualification.objects.create(
            person=self.instructor, machine=self.machine, is_instructor=True
        )

    def test_instructed_by_scoped_to_machine_instructors(self):
        form = BulkQualifyForm(machine=self.machine)
        queryset = form.fields["instructed_by"].queryset
        self.assertIn(self.instructor, queryset)
        self.assertNotIn(self.other_person, queryset)

    def test_instructed_by_unscoped_without_machine(self):
        form = BulkQualifyForm()
        queryset = form.fields["instructed_by"].queryset
        self.assertIn(self.instructor, queryset)
        self.assertIn(self.other_person, queryset)


class BulkQualifyServiceTests(TestCase):
    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        self.person_a = Person.objects.create(name="a", email="a@example.com")
        self.person_b = Person.objects.create(name="b", email="b@example.com")

    def test_qualifies_multiple_people_for_one_machine(self):
        qualifications = bulk_qualify(
            machine=self.machine,
            people=[self.person_a, self.person_b],
            permission_level="if_space_open",
        )
        self.assertEqual(len(qualifications), 2)
        self.assertEqual(
            Qualification.objects.filter(machine=self.machine).count(), 2
        )

    def test_qualifies_one_person_for_multiple_machines(self):
        other_machine = Machine.objects.create(
            mac_address="11:22:33:44:55:66", hostname="test2", name="test2"
        )
        qualifications = bulk_qualify(
            person=self.person_a,
            machines=[self.machine, other_machine],
            permission_level="if_space_open",
        )
        self.assertEqual(len(qualifications), 2)
        self.assertEqual(
            Qualification.objects.filter(person=self.person_a).count(), 2
        )

    def test_existing_pair_is_not_duplicated(self):
        Qualification.objects.create(person=self.person_a, machine=self.machine)
        bulk_qualify(
            machine=self.machine,
            people=[self.person_a],
            permission_level="if_space_open",
        )
        self.assertEqual(
            Qualification.objects.filter(
                person=self.person_a, machine=self.machine
            ).count(),
            1,
        )
