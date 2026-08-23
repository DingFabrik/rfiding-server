from django import forms
from django.test import TestCase

from machines.fields import WeekdayFormField
from machines.models import Machine, MachineTime
from machines.utils import DAY_CHOICES


class WeekdayFormFieldTests(TestCase):
    def test_defaults_to_day_choices_and_select_multiple_widget(self):
        field = WeekdayFormField()
        self.assertEqual(field.choices, list(DAY_CHOICES))
        self.assertIsInstance(field.widget, forms.widgets.SelectMultiple)

    def test_respects_custom_choices_and_widget(self):
        custom_choices = (("a", "A"),)
        custom_widget = forms.widgets.CheckboxSelectMultiple
        field = WeekdayFormField(choices=custom_choices, widget=custom_widget)
        self.assertEqual(field.choices, list(custom_choices))
        self.assertIsInstance(field.widget, custom_widget)

    def test_drops_max_length_kwarg(self):
        field = WeekdayFormField(max_length=20)
        self.assertNotIn("max_length", field.widget_attrs(field.widget))


class WeekdayFieldTests(TestCase):
    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )

    def test_stores_and_reloads_weekday_list(self):
        machine_time = MachineTime.objects.create(
            machine=self.machine,
            weekdays=[0, 2, 4],
            start_time="08:00",
            end_time="18:00",
        )
        machine_time.refresh_from_db()
        self.assertEqual(machine_time.weekdays, [0, 2, 4])

    def test_empty_weekdays_round_trips_to_empty_list(self):
        machine_time = MachineTime.objects.create(
            machine=self.machine,
            weekdays=[],
            start_time="08:00",
            end_time="18:00",
        )
        machine_time.refresh_from_db()
        self.assertEqual(machine_time.weekdays, [])

    def test_to_python_parses_bracketed_string(self):
        field = MachineTime._meta.get_field("weekdays")
        self.assertEqual(field.to_python("[1,2,3]"), [1, 2, 3])
        self.assertEqual(field.to_python(""), [])
        self.assertEqual(field.to_python([1, 2]), [1, 2])

    def test_get_db_prep_value_serializes_list(self):
        field = MachineTime._meta.get_field("weekdays")
        self.assertEqual(field.get_db_prep_value([1, 2, 3]), "1,2,3")
        self.assertEqual(field.get_db_prep_value(None), "")
        self.assertEqual(field.get_db_prep_value([]), "")


class MachineTimeDisplayTests(TestCase):
    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )

    def make_time(self, weekdays):
        return MachineTime.objects.create(
            machine=self.machine,
            weekdays=weekdays,
            start_time="08:00",
            end_time="18:00",
        )

    def test_all_seven_days_displays_as_everyday(self):
        self.assertEqual(self.make_time([0, 1, 2, 3, 4, 5, 6]).get_weekdays_display(), "Everyday")

    def test_empty_displays_as_everyday(self):
        self.assertEqual(self.make_time([]).get_weekdays_display(), "Everyday")

    def test_monday_to_friday_displays_as_weekdays(self):
        self.assertEqual(self.make_time([0, 1, 2, 3, 4]).get_weekdays_display(), "Weekdays")

    def test_saturday_sunday_displays_as_weekends(self):
        self.assertEqual(self.make_time([5, 6]).get_weekdays_display(), "Weekends")

    def test_arbitrary_combination_lists_day_names(self):
        machine_time = self.make_time([0, 2, 4])
        self.assertEqual(
            machine_time.get_weekdays_display(), "Monday, Wednesday, Friday"
        )

    def test_str_includes_weekday_display_and_times(self):
        machine_time = self.make_time([0, 2, 4])
        self.assertIn("Monday, Wednesday, Friday", str(machine_time))
