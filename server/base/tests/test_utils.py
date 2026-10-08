from django.http import QueryDict
from django.test import SimpleTestCase

from base.utils import get_int_list


class GetIntListTests(SimpleTestCase):
    def test_parses_integers(self):
        self.assertEqual(get_int_list(QueryDict("ids=1&ids=22"), "ids"), [1, 22])

    def test_drops_malformed_values(self):
        self.assertEqual(
            get_int_list(QueryDict("ids=&ids=abc&ids=-1&ids=1.5&ids=3"), "ids"), [3]
        )

    def test_missing_key(self):
        self.assertEqual(get_int_list(QueryDict(""), "ids"), [])
