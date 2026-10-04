from django.contrib.auth import get_user_model
from django.http import QueryDict
from django.test import TestCase
from django.urls import reverse

from access_log.filters import AccessLogApiFilterSet, AccessLogFilterSet
from access_log.models import (
    AccessLog,
    LOG_TYPE_BOOTED,
    LOG_TYPE_DISABLED,
    LOG_TYPE_ENABLED,
    LOG_TYPE_UNSUCCESSFUL,
    UnsuccessfulReason,
)
from machines.models import Machine


class AccessLogFilterTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            email="admin@example.com", password="pass"
        )
        self.client.force_login(self.user)
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="test", name="test"
        )
        self.booted = self.create_log(LOG_TYPE_BOOTED)
        self.enabled = self.create_log(LOG_TYPE_ENABLED)
        self.disabled = self.create_log(LOG_TYPE_DISABLED)
        self.unsuccessful = self.create_log(
            LOG_TYPE_UNSUCCESSFUL, unsuccessful_reason=UnsuccessfulReason.NOT_QUALIFIED
        )

    def create_log(self, log_type, **kwargs):
        return AccessLog.objects.create(machine=self.machine, type=log_type, **kwargs)

    def get_list(self, query=""):
        return self.client.get(reverse("access_log:list") + query)

    def test_default_hides_unsuccessful(self):
        response = self.get_list()
        self.assertCountEqual(
            response.context["access_logs"], [self.booted, self.enabled, self.disabled]
        )
        self.assertEqual(
            response.context["filter_choices"]["action"]["value"],
            [LOG_TYPE_BOOTED, "registered", LOG_TYPE_ENABLED, LOG_TYPE_DISABLED],
        )

    def test_renders_checkboxes_with_default_state(self):
        response = self.get_list()
        self.assertContains(response, 'type="checkbox"', count=5)
        self.assertContains(response, 'value="enabled"\n                        checked')
        self.assertNotContains(response, 'value="unsuccessful"\n                        checked')

    def test_select_multiple_types(self):
        response = self.get_list("?filter_action=&filter_action=enabled&filter_action=unsuccessful")
        self.assertCountEqual(
            response.context["access_logs"], [self.enabled, self.unsuccessful]
        )
        self.assertContains(response, 'value="unsuccessful"\n                        checked')

    def test_only_unsuccessful_shows_reason(self):
        response = self.get_list("?filter_action=&filter_action=unsuccessful")
        self.assertEqual(list(response.context["access_logs"]), [self.unsuccessful])
        self.assertContains(response, "Not qualified")

    def test_nothing_checked_shows_nothing(self):
        response = self.get_list("?filter_action=")
        self.assertEqual(list(response.context["access_logs"]), [])

    def test_pagination_keeps_all_selected_types(self):
        self.user.page_length = 1
        self.user.save()
        response = self.get_list("?filter_action=&filter_action=enabled&filter_action=disabled")
        self.assertContains(
            response, "filter_action=&amp;filter_action=enabled&amp;filter_action=disabled&amp;page=2"
        )

    def test_comma_separated_values(self):
        filterset = AccessLogFilterSet(
            QueryDict("filter_action=booted,unsuccessful"), AccessLog.objects.all()
        )
        self.assertCountEqual(filterset.qs, [self.booted, self.unsuccessful])

    def test_api_filterset_defaults_to_all_types(self):
        filterset = AccessLogApiFilterSet(QueryDict(), AccessLog.objects.all())
        self.assertEqual(filterset.qs.count(), 4)

    def test_all_value_disables_filter(self):
        filterset = AccessLogApiFilterSet(
            QueryDict("filter_action=all"), AccessLog.objects.all()
        )
        self.assertEqual(filterset.qs.count(), 4)
