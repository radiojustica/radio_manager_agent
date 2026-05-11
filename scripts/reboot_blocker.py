import ctypes
import os
import winreg
import logging
import subprocess

# Define flags for SetThreadExecutionState
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

class RebootBlocker:
    def __init__(self):
        self.logger = logging.getLogger("RadioManagerAgent.RebootBlocker")

    def prevent_sleep(self):
        """Prevents the system from entering sleep mode."""
        try:
            res = ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            )
            if res == 0:
                self.logger.error("Failed to set thread execution state.")
            else:
                self.logger.info("System sleep/display timeout prevented.")
        except Exception as e:
            self.logger.error(f"Error in prevent_sleep: {e}")

    def apply_registry_blocks(self):
        """Sets registry keys to disable automatic reboots for Window Updates."""
        reg_path = r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, reg_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "NoAutoRebootWithLoggedOnUsers", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            self.logger.info("Registry block 'NoAutoRebootWithLoggedOnUsers' applied.")
        except PermissionError:
            self.logger.error("Need admin privileges to apply registry blocks.")
        except Exception as e:
            self.logger.error(f"Error applying registry blocks: {e}")

    def abort_shutdown(self):
        """Attempts to abort an ongoing shutdown command."""
        try:
            # Using shell command to abort any scheduled shutdown
            subprocess.run(["shutdown", "/a"], capture_output=True, check=False)
            self.logger.debug("Attempted to abort any pending shutdown.")
        except Exception as e:
            self.logger.error(f"Error aborting shutdown: {e}")

    def block_shutdown(self, reason="Radio Station in Broadcast"):
        """
        Note: This usually requires a window (HWND) and is complex for a console app.
        For now, we rely on registry and power state.
        """
        pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    rb = RebootBlocker()
    rb.prevent_sleep()
    rb.apply_registry_blocks()


