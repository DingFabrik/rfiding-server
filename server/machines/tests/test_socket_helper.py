import json
import socket
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from machines import socket_helper


class SendSocketActionTests(TestCase):
    @override_settings(ENABLE_CLIENT_API=False)
    def test_disabled_is_a_noop(self):
        with patch("machines.socket_helper.ENABLE", False):
            with patch("socket.socket") as mock_socket:
                socket_helper.send_socket_action(1, "enable")
        mock_socket.assert_not_called()

    def test_sends_json_message_over_socket(self):
        mock_conn = MagicMock()
        with patch("machines.socket_helper.ENABLE", True):
            with patch("socket.socket") as mock_socket_cls:
                mock_socket_cls.return_value.__enter__.return_value = mock_conn
                socket_helper.send_socket_action(42, "enable")

        mock_conn.connect.assert_called_once_with(
            (socket_helper.SOCKET_IP, socket_helper.SOCKET_PORT)
        )
        sent = json.loads(mock_conn.sendall.call_args[0][0].decode())
        self.assertEqual(sent, {"action": "enable", "pk": 42})

    def test_socket_error_is_caught_and_logged(self):
        with patch("machines.socket_helper.ENABLE", True):
            with patch("socket.socket") as mock_socket_cls:
                mock_socket_cls.return_value.__enter__.side_effect = socket.error(
                    "boom"
                )
                # Should not raise.
                socket_helper.send_socket_action(1, "enable")


class GetSocketDataTests(TestCase):
    def test_disabled_returns_none(self):
        with patch("machines.socket_helper.ENABLE", False):
            with patch("socket.socket") as mock_socket:
                result = socket_helper.get_socket_data(1, "status")
        self.assertIsNone(result)
        mock_socket.assert_not_called()

    def test_returns_decoded_response(self):
        mock_conn = MagicMock()
        mock_conn.recv.return_value = b"enabled"
        with patch("machines.socket_helper.ENABLE", True):
            with patch("socket.socket") as mock_socket_cls:
                mock_socket_cls.return_value.__enter__.return_value = mock_conn
                result = socket_helper.get_socket_data(1, "status")

        self.assertEqual(result, "enabled")

    def test_socket_error_returns_none(self):
        with patch("machines.socket_helper.ENABLE", True):
            with patch("socket.socket") as mock_socket_cls:
                mock_socket_cls.return_value.__enter__.side_effect = socket.error(
                    "boom"
                )
                result = socket_helper.get_socket_data(1, "status")

        self.assertIsNone(result)
