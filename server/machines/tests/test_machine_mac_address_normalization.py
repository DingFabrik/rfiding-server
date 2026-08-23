from django.test import TestCase
from machines.models import Machine


class MachineMacAddressNormalizationTests(TestCase):
    def test_save_lowercases_mac_address(self):
        machine = Machine.objects.create(
            mac_address="AA:BB:CC:DD:EE:FF", hostname="test", name="test"
        )
        machine.refresh_from_db()
        self.assertEqual(machine.mac_address, "aa:bb:cc:dd:ee:ff")

    def test_save_with_no_mac_address_is_a_noop(self):
        machine = Machine.objects.create(hostname="test", name="test")
        machine.refresh_from_db()
        self.assertIsNone(machine.mac_address)
