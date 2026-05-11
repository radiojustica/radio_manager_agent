import pytest
import os
import sys
from unittest.mock import MagicMock, patch

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.monitor import RadioMonitor

class TestRadioMonitor:
    @pytest.fixture
    def monitor(self):
        # Create instance without calling __init__ to avoid side effects during setup
        m = RadioMonitor.__new__(RadioMonitor)
        m.config_path = "mock_config.json"
        m.settings = {
            "apps": {
                "zararadio": {"process_name": "ZaraRadio.exe"},
                "butt": {"process_name": "butt.exe"}
            },
            "monitoring": {"interval_seconds": 60}
        }
        m.reboot_blocker = MagicMock()
        m.audio_manager = MagicMock()
        m.logger = MagicMock()
        return m

    def test_monitor_initialization(self, monitor):
        assert monitor is not None
        assert hasattr(monitor, 'reboot_blocker')
        assert hasattr(monitor, 'audio_manager')

    def test_get_current_block_hour(self, monitor):
        # This test ensures the block hour is always even (0, 2, 4...)
        hour = monitor.get_current_block_hour()
        assert hour % 2 == 0
        assert 0 <= hour <= 22

    @patch('subprocess.check_output')
    def test_check_processes(self, mock_check, monitor):
        # Simulate ZaraRadio.exe and butt.exe running
        mock_check.return_value = b"ZaraRadio.exe exists\nbutt.exe exists"
        status = monitor.check_processes()
        
        assert status.get("zararadio") == "Running"
        assert status.get("butt") == "Running"

    def test_get_target_playlist(self, monitor):
        # Verify if playlist path follows the pattern PROG_XXH.m3u
        playlist = monitor.get_target_playlist()
        assert "PROG_" in playlist
        assert ".m3u" in playlist


