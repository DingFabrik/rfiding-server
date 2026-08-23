from django.test import TestCase
from ..models import Holiday
from ..utils import get_holiday_by_date, is_holiday, is_today_holiday
from django.utils import timezone


class HolidayUtilsTests(TestCase):
    def setUp(self):
        global cached_holiday, cached_date
        cached_holiday = None
        cached_date = None
        self.repeating_date = timezone.datetime.now().date()
        self.repeating_date += timezone.timedelta(days=1)  # Ensure it's a future date
        self.repeating_holiday = Holiday.objects.create(
            name="Test Holiday",
            date=self.repeating_date,
            repeats_annually=True
        )
        self.test_date = timezone.datetime(2024, 12, 25).date()
        self.non_repeating_holiday = Holiday.objects.create(
            name="Christmas",
            date=self.test_date,
            repeats_annually=False
        )

    def test_get_holiday_by_date_found(self):
        holiday = get_holiday_by_date(self.repeating_date)
        self.assertIsNotNone(holiday)
        self.assertEqual(holiday.name, "Test Holiday")
        
    def test_get_repeating_holiday_by_different_year(self):
        test_date_different_year = self.repeating_date.replace(year=self.repeating_date.year + 1)
        holiday = get_holiday_by_date(test_date_different_year)
        self.assertIsNotNone(holiday)
        self.assertEqual(holiday.name, "Test Holiday")
        
    def test_get_non_repeating_holiday_by_date(self):
        holiday = get_holiday_by_date(self.test_date)
        self.assertIsNotNone(holiday)
        self.assertEqual(holiday.name, "Christmas")
        
    def test_get_non_repeating_holiday_by_different_date(self):
        different_date = self.test_date + timezone.timedelta(days=1)
        holiday = get_holiday_by_date(different_date)
        self.assertIsNone(holiday)

    def test_get_holiday_by_date_not_found(self):
        holiday = get_holiday_by_date(timezone.datetime(2024, 1, 1).date())
        self.assertIsNone(holiday)

    def test_is_holiday_true(self):
        result = is_holiday(self.repeating_date)
        self.assertTrue(result)

    def test_is_holiday_false(self):
        result = is_holiday(timezone.datetime(2024, 1, 1).date())
        self.assertFalse(result)

    def test_is_today_holiday(self):
        result = is_today_holiday(True)
        self.assertFalse(result)
        
    def test_is_today_holiday_with_holiday(self):
        today = timezone.localdate()
        Holiday.objects.create(
            name="Today's Holiday",
            date=today
        )
        result = is_today_holiday(True)
        self.assertTrue(result)
