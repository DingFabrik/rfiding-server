from django.test import TestCase
from ..models import Holiday


class HolidayModelTests(TestCase):
    def test_create_holiday(self):
        holiday = Holiday.objects.create(
            name="Test Holiday",
            date="2024-12-25",
            repeats_annually=True
        )
        self.assertEqual(holiday.name, "Test Holiday")
        self.assertEqual(holiday.date, "2024-12-25")
        self.assertTrue(holiday.repeats_annually)
        
    def test_holiday_str(self):
        holiday = Holiday.objects.create(
            name="Test Holiday",
            date="2024-12-25",
            repeats_annually=True
        )
        self.assertEqual(str(holiday), "Test Holiday on 2024-12-25")
