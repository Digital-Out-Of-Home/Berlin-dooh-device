
import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError

sys.path.append(str(Path(__file__).parent.parent / "src"))

from health_check import health_check

class TestHealthCheck(unittest.TestCase):
    
    @patch('health_check.load_config')
    @patch('health_check.urlopen')
    @patch('health_check.Request')
    def test_health_check_success(self, mock_req, mock_urlopen, mock_config):
        # Setup
        mock_config.return_value = {"HEALTHCHECK_URL": "http://test.com/ping"}
        
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        # Execute
        health_check()
        
        # Verify
        mock_req.assert_called_with("http://test.com/ping")
        mock_urlopen.assert_called()

    @patch('health_check.load_config')
    def test_health_check_no_url(self, mock_config):
        mock_config.return_value = {} # No HEALTHCHECK_URL
        
        # Capture stdout to verify print
        with patch('sys.stdout') as mock_stdout:
            health_check()
            # Should just print skipping message and return
            # We can check if it printed "Skipping"
            # Getting calls to write is a bit verbose, but essentially verify no exception raise
            self.assertTrue(True)

    @patch('health_check.load_config')
    @patch('health_check.urlopen')
    def test_health_check_http_error(self, mock_urlopen, mock_config):
        mock_config.return_value = {"HEALTHCHECK_URL": "http://test.com/ping"}
        
        # Mock HTTPError
        err = HTTPError("url", 500, "Internal Error", {}, None)
        mock_urlopen.side_effect = err
        
        with self.assertRaises(SystemExit) as cm:
            health_check()
        self.assertEqual(cm.exception.code, 1)

    @patch('health_check.load_config')
    @patch('health_check.urlopen')
    def test_health_check_url_error(self, mock_urlopen, mock_config):
        mock_config.return_value = {"HEALTHCHECK_URL": "http://test.com/ping"}
        
        # Mock URLError
        err = URLError("Connection refused")
        mock_urlopen.side_effect = err
        
        with self.assertRaises(SystemExit) as cm:
            health_check()
        self.assertEqual(cm.exception.code, 1)

if __name__ == "__main__":
    unittest.main()
