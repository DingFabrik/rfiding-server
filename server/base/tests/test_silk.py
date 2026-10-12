from django.test import RequestFactory, SimpleTestCase, override_settings

from base.silk import should_record


class ShouldRecordTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(SILKY_INTERCEPT_PERCENT=100)
    def test_records_requests(self):
        self.assertTrue(should_record(self.factory.get("/machines/")))

    @override_settings(SILKY_INTERCEPT_PERCENT=100)
    def test_never_records_oauth_endpoints(self):
        for path in ("/api/rest/v1/oauth/token/", "/api/rest/v1/oauth/applications/"):
            self.assertFalse(should_record(self.factory.post(path)), path)

    @override_settings(SILKY_INTERCEPT_PERCENT=0)
    def test_records_nothing_at_zero_percent(self):
        self.assertFalse(any(should_record(self.factory.get("/")) for _ in range(100)))

    @override_settings(SILKY_INTERCEPT_PERCENT=10)
    def test_records_a_sample(self):
        recorded = sum(should_record(self.factory.get("/")) for _ in range(2000))
        self.assertGreater(recorded, 100)
        self.assertLess(recorded, 300)
