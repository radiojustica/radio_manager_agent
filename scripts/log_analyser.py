import os
import glob
import logging
from datetime import datetime

class LogAnalyser:
    def __init__(self, settings):
        self.logger = logging.getLogger("RadioManagerAgent.LogAnalyser")
        self.settings = settings
        self.last_read_lines = {}

    def get_latest_log(self, app_name):
        """Finds the most recently modified log file for the specified application."""
        app_settings = self.settings.get("apps", {}).get(app_name, {})
        log_dir = app_settings.get("log_path", "")
        pattern = app_settings.get("search_log_pattern", "*.log")

        if not os.path.exists(log_dir):
            self.logger.warning(f"Log directory for {app_name} not found: {log_dir}")
            return None

        files = glob.glob(os.path.join(log_dir, pattern))
        if not files:
            return None

        # Return latest modified file
        return max(files, key=os.path.getmtime)

    def analyse_zararadio(self):
        """Reads latest ZaraRadio logs to track program execution."""
        log_file = self.get_latest_log("zararadio")
        if not log_file:
            return []

        # Read new lines since last check
        new_lines = []
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.readlines()
                # Simple logic: check last 10 lines for now
                for line in content[-10:]:
                    if line.strip():
                        new_lines.append(line.strip())
        except Exception as e:
            self.logger.error(f"Error reading ZaraRadio log: {e}")

        return new_lines

    def analyse_butt(self):
        """BUTT log analysis - placeholder if file is found."""
        log_file = self.get_latest_log("butt")
        if not log_file:
             return ["Status: Unknown (Log not found/configured)"]
        return []

if __name__ == "__main__":
    import json
    import sys
    logging.basicConfig(level=logging.INFO)
    # Mock settings for testing
    mock_settings = {
        "apps": {
            "zararadio": {"log_path": "C:\\ZaraRadio\\Log", "search_log_pattern": "*.log"},
            "butt": {"log_path": "", "search_log_pattern": "*.log"}
        }
    }
    la = LogAnalyser(mock_settings)
    print(la.analyse_zararadio())


