
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
    def setUp(self):
        # Save original environ
        self.original_environ = dict(os.environ)

    def tearDown(self):
        # Restore original environ
        os.environ.clear()
        os.environ.update(self.original_environ)

    def test_get_device_id_configured(self):
        """Test that configured DEVICE_ID is returned."""
        os.environ["DEVICE_ID"] = "test-device-123"
        self.assertEqual(get_device_id(), "test-device-123")

    def test_get_device_id_fallback(self):
        """Test fallback to hostname when DEVICE_ID is not set."""
        if "DEVICE_ID" in os.environ:
            del os.environ["DEVICE_ID"]
        expected_hostname = socket.gethostname()
        self.assertEqual(get_device_id(), expected_hostname)

    def test_load_config_defaults(self):
        """Test that load_config returns expected defaults when no config file."""
        # Ensure we don't accidentally read a real config file by patching BASE_DIR or ensuring env vars are clear
        # Ideally we'd patch BASE_DIR in the module, but for now assuming no config.env in test env or ignored if env vars set
        
        # Clear specific env vars
        keys = ["API_URL", "API_TOKEN", "DEVICE_ID", "HOST_URL", "HEALTHCHECK_URL"]
        for k in keys:
            if k in os.environ:
                del os.environ[k]
                
        config = load_config()
        self.assertEqual(config["API_URL"], "http://host.docker.internal:8000/api/v1/campaign/playlist/")
        self.assertEqual(config["HOST_URL"], "http://host.docker.internal:8000")
        self.assertEqual(config["API_TOKEN"], "temporary_device_token_123456")

if __name__ == "__main__":
    unittest.main()
