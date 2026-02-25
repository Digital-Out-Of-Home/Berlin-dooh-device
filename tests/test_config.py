
import unittest
import os
import socket
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add src to path so we can import modules
sys.path.append(str(Path(__file__).parent.parent / "src"))

from config import get_device_id, load_config

class TestConfig(unittest.TestCase):
    @patch('config._read_env_file')
    def test_get_device_id_configured(self, mock_read_env):
        """Test that configured DEVICE_ID is returned."""
        mock_read_env.return_value = {"DEVICE_ID": "test-device-123"}
        self.assertEqual(get_device_id(), "test-device-123")

    @patch('config._read_env_file')
    def test_get_device_id_fallback(self, mock_read_env):
        """Test fallback to hostname when DEVICE_ID is not set."""
        mock_read_env.return_value = {}
        expected_hostname = socket.gethostname()
        self.assertEqual(get_device_id(), expected_hostname)

    @patch('config._read_env_file')
    def test_load_config_defaults(self, mock_read_env):
        """Test that load_config returns expected defaults when no config file."""
        mock_read_env.return_value = {}
        config = load_config()
        self.assertEqual(config["API_URL"], "https://piapi.speakinprivate.com/api/v1/campaign/playlist/")
        self.assertEqual(config["HOST_URL"], "https://piapi.speakinprivate.com")
        self.assertEqual(config["API_TOKEN"], "")

if __name__ == "__main__":
    unittest.main()
