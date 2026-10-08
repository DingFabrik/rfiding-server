from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from machines import checks
from machines.models import Machine

REDIS_LAYER = "channels_redis.core.RedisChannelLayer"
MEMORY_LAYER = "channels.layers.InMemoryChannelLayer"


def ids(messages):
    return [message.id for message in messages]


# Patches the backend lookup instead of overriding CHANNEL_LAYERS: that would
# make channels drop its layers, breaking consumer tests that run afterwards.
class ClientApiChannelLayerCheckTests(SimpleTestCase):
    def run_check(self, backend):
        with patch.object(checks, "channel_layer_backend", return_value=backend):
            return ids(checks.check_client_api_channel_layer(None))

    @override_settings(ENABLE_CLIENT_API=True)
    def test_shared_layer(self):
        self.assertEqual(self.run_check(REDIS_LAYER), [])

    @override_settings(ENABLE_CLIENT_API=True)
    def test_in_memory_layer(self):
        self.assertEqual(self.run_check(MEMORY_LAYER), ["machines.E001"])

    @override_settings(ENABLE_CLIENT_API=True)
    def test_missing_layer(self):
        self.assertEqual(self.run_check(None), ["machines.E001"])

    @override_settings(ENABLE_CLIENT_API=False)
    def test_client_api_disabled(self):
        self.assertEqual(self.run_check(MEMORY_LAYER), [])


class NativeApiMachinesCheckTests(TestCase):
    def setUp(self):
        self.machine = Machine.objects.create(
            mac_address="aa:bb:cc:dd:ee:ff", hostname="locker", name="Locker"
        )

    def run_check(self):
        return ids(checks.check_native_api_machines(None, databases=["default"]))

    def set_encryption_key(self, key):
        Machine.objects.filter(pk=self.machine.pk).update(encryption_key=key)

    @override_settings(ENABLE_CLIENT_API=False)
    def test_no_native_api_machines(self):
        self.set_encryption_key("")
        self.assertEqual(self.run_check(), [])

    @override_settings(ENABLE_CLIENT_API=False)
    def test_native_api_machine_without_client_api(self):
        self.set_encryption_key("c2VjcmV0LWtleS1mb3ItdGVzdGluZy0xMjM0NTY3OA==")
        self.assertEqual(self.run_check(), ["machines.W001"])

    @override_settings(ENABLE_CLIENT_API=True)
    def test_native_api_machine_with_client_api(self):
        self.set_encryption_key("c2VjcmV0LWtleS1mb3ItdGVzdGluZy0xMjM0NTY3OA==")
        self.assertEqual(self.run_check(), [])


class TokenIdMaxLengthCheckTests(SimpleTestCase):
    def run_check(self, value):
        with override_settings(TOKEN_ID_MAX_LENGTH=value):
            return [e.id for e in checks.check_token_id_max_length(None)]

    def test_valid_values_pass(self):
        for value in (None, 1, 8, 14):
            self.assertEqual(self.run_check(value), [], value)

    def test_invalid_values_error(self):
        for value in (0, -2, "8", 8.0, True):
            self.assertEqual(self.run_check(value), ["machines.E002"], value)
