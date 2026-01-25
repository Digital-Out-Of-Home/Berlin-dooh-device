
import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "src"))

# We import the module to test functions, but we need to be careful about module-level execution
# Since media_sync doesn't have a main guard block that prevents execution on import (it has if __name__ == "__main__"), it is safe to import.
import media_sync

class TestMediaSync(unittest.TestCase):

    @patch('media_sync.load_config')
    def setUp(self, mock_loader):
        # Setup common mocks
        pass

    @patch('media_sync.SYNC_LOCK')
    @patch('media_sync.time')
    @patch('media_sync.os')
    def test_acquire_lock_fresh(self, mock_os, mock_time, mock_lock_path):
        """Test acquiring lock when no lock exists."""
        mock_lock_path.exists.return_value = False
        mock_time.time.return_value = 1000.0
        mock_os.getpid.return_value = 12345
        
        result = media_sync.acquire_lock(force=False)
        
        self.assertTrue(result)
        mock_lock_path.write_text.assert_called_with("12345:1000.0\n")

    @patch('media_sync.SYNC_LOCK')
    @patch('media_sync.is_process_running')
    def test_acquire_lock_running_no_force(self, mock_is_running, mock_lock_path):
        """Test active lock prevents execution without force."""
        mock_lock_path.exists.return_value = True
        mock_lock_path.read_text.return_value = "999:2000.0" 
        
        # Simulate active process and fresh timestamp (now is 2010.0)
        with patch('media_sync.time.time', return_value=2010.0):
            mock_is_running.return_value = True
            
            result = media_sync.acquire_lock(force=False)
            
            self.assertFalse(result)

    @patch('media_sync.urlopen')
    @patch('media_sync.Request')
    def test_fetch_campaigns(self, mock_req, mock_urlopen):
        """Test fetching campaigns from API."""
        # Setup mock response
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps([{"media_file": "vid.mp4"}]).encode('utf-8')
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp
        
        # Configure global API_URL via patch or by setting it in the module if safe (better to patch config loading but here we already imported)
        # The module loaded config at top level. We can patch the global variable in the module.
        with patch.object(media_sync, 'API_URL', 'http://api.com'):
             campaigns = media_sync.fetch_campaigns("dev1")
             
             self.assertEqual(len(campaigns), 1)
             self.assertEqual(campaigns[0]["media_file"], "vid.mp4")

    @patch('media_sync.MEDIA_DIR')
    def test_generate_playlist_content(self, mock_media_dir):
        """Test m3u content generation."""
        # Mock Path string representation for consistency
        mock_media_dir.__str__.return_value = "/local/media"
        # Since Path / string behavior is tricky with MagicMock, let's just rely on basic logic
        # Ideally we'd use pyfakefs but we stick to standard unittest
        
        campaigns = [
            {"media_file": "campaigns/movie.mp4"}
        ]
        
        # We need to make sure the joining logic works. 
        # media_sync.py uses MEDIA_DIR / filename
        # We can simulate this by making mock_media_dir / "movie.mp4" return a specific path
        mock_file_path = MagicMock()
        mock_file_path.__str__.return_value = "/local/media/movie.mp4"
        mock_media_dir.__truediv__.return_value = mock_file_path
        
        content = media_sync.generate_playlist_content(campaigns)
        
        self.assertIn("#EXTM3U", content)
        self.assertIn("server-url=\"campaigns/movie.mp4\"", content)
        self.assertIn("/local/media/movie.mp4", content)

    @patch('media_sync.download_media_file')
    @patch('media_sync.fetch_campaigns')
    @patch('media_sync.acquire_lock')
    @patch('media_sync.get_device_id')
    @patch('media_sync.MEDIA_DIR')
    def test_sync_logic_download(self, mock_media_dir, mock_get_did, mock_lock, mock_fetch, mock_download):
        """Test sync logic triggers download for missing files."""
        mock_lock.return_value = True
        mock_get_did.return_value = "d1"
        mock_fetch.return_value = [{"media_file": "new_video.mp4"}]
        
        # Setup local state: playlist empty, no files
        mock_playlist_path = MagicMock()
        # Mock get_playlist_media_names to return different set
        with patch('media_sync.get_playlist_media_names', return_value=set()):
            # Mock iterdir to return empty
            mock_media_dir.iterdir.return_value = []
            mock_media_dir.__truediv__.return_value = mock_playlist_path

            media_sync.sync()
            
            # Verify download was called
            mock_download.assert_called()
            # Verify playlist update
            mock_playlist_path.write_text.assert_called()

if __name__ == "__main__":
    unittest.main()
