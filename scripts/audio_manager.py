from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume, IAudioMeterInformation
import comtypes
import logging
import threading

class AudioManager:
    def __init__(self, limit: float = 0.24):
        self.limit = limit  # Default limit: 24%
        self.logger = logging.getLogger("RadioManagerAgent.AudioManager")
        self._cached_device = None
        self._cached_device_name = None
        self._cached_meter = None
        self._lock = threading.Lock()

    def _find_sessions(self, process_name: str):
        """Yields all audio sessions matching the given process name."""
        try:
            comtypes.CoInitialize()
        except:
            pass
        sessions = AudioUtilities.GetAllSessions()
        name_lower = process_name.lower()
        for session in sessions:
            matched = False
            if session.Process and session.Process.name().lower() == name_lower:
                matched = True
            elif session.Identifier and name_lower in session.Identifier.lower():
                matched = True
            if matched:
                yield session

    def limit_app_volume(self, process_name: str, limit: float = None) -> bool:
        target_limit = limit if limit is not None else self.limit
        found_any = False
        try:
            for session in self._find_sessions(process_name):
                found_any = True
                volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                current_volume = volume.GetMasterVolume()
                if limit is not None or current_volume > target_limit:
                    volume.SetMasterVolume(target_limit, None)
        except Exception as e:
            self.logger.error(f"Error limiting volume for '{process_name}': {e}")
            return False
        return found_any

    def get_process_peak(self, process_name: str) -> float:
        try:
            for session in self._find_sessions(process_name):
                meter = session._ctl.QueryInterface(IAudioMeterInformation)
                return meter.GetPeakValue()
        except Exception as e:
            self.logger.error(f"Error getting peak for '{process_name}': {e}")
        return -1.0

    def get_master_peak(self, device_name: str = "RADIO") -> float:
        """Returns the master audio peak level. Thread-safe and high performance."""
        with self._lock:
            try:
                try: comtypes.CoInitialize()
                except: pass

                # 1. Reuse cached meter if possible
                if self._cached_meter and self._cached_device_name == device_name:
                    try:
                        return self._cached_meter.GetPeakValue()
                    except:
                        self._cached_meter = None

                # 2. Discover device if not cached
                if not self._cached_device or self._cached_device_name != device_name:
                    devices = AudioUtilities.GetAllDevices()
                    target_device = None
                    for d in devices:
                        if device_name.lower() in d.FriendlyName.lower():
                            target_device = d
                            break
                    if not target_device:
                        target_device = AudioUtilities.GetSpeakers()
                    
                    self._cached_device = target_device
                    self._cached_device_name = device_name
                    self._cached_meter = None

                # 3. Activate meter interface
                if not self._cached_meter:
                    interface = self._cached_device._dev.Activate(
                        IAudioMeterInformation._iid_, comtypes.CLSCTX_ALL, None
                    )
                    self._cached_meter = interface.QueryInterface(IAudioMeterInformation)
                
                return self._cached_meter.GetPeakValue()

            except Exception as e:
                self.logger.error(f"Error getting master peak for device '{device_name}': {e}")
                self._cached_meter = None
                self._cached_device = None
                return -1.0
            finally:
                try: comtypes.CoUninitialize()
                except: pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    am = AudioManager()
    print(f"Master Peak: {am.get_master_peak('RADIO')}")


