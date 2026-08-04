from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume, IAudioMeterInformation
import comtypes
import logging
import threading

# ⚠️ SEGURANÇA ACÚSTICA (REGRAS NÃO NEGOCIÁVEIS DO TJRN):
#   1. ZaraRadio NUNCA deve modificar o dispositivo de áudio.
#   2. O SISTEMA NUNCA deve modificar o volume (afeta a qualidade do stream).
# Por isso esta classe é ESTRITAMENTE SOMENTE-LEITURA: ela só observa/ Mede.
# Nenhum método aqui chama SetMasterVolume / SetVolume / altera dispositivo.


class AudioManager:
    def __init__(self, limit: float = 0.24):
        # `limit` é usado APENAS como referência para AVISOS (leitura), nunca para aplicar.
        self.limit = limit
        self.logger = logging.getLogger("RadioManagerAgent.AudioManager")
        self._cached_device = None
        self._cached_device_name = None
        self._cached_meter = None
        self._lock = threading.Lock()

    def _find_sessions(self, process_name: str):
        """Yields all audio sessions matching the given process name (read-only)."""
        try:
            comtypes.CoInitialize()
        except Exception:
            # Já inicializado na thread ou erro não crítico
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

    def get_app_volume(self, process_name: str) -> float:
        """Lê (NUNCA altera) o volume master da sessão do processo. Retorna -1.0 se indisponível."""
        try:
            for session in self._find_sessions(process_name):
                volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                return volume.GetMasterVolume()
        except Exception as e:
            self.logger.error(f"Erro ao ler volume de '{process_name}': {e}")
        return -1.0

    def check_volume_safety(self, process_name: str, limit: float = None) -> dict:
        """
        Apenas INFORMA se o volume está acima do limite de referência.
        NÃO modifica nada. Retorna um dicionário para o chamador decidir (ex.: logar aviso).
        """
        target_limit = limit if limit is not None else self.limit
        current = self.get_app_volume(process_name)
        return {
            "process": process_name,
            "current_volume": current,
            "reference_limit": target_limit,
            "over_limit": current > target_limit if current >= 0 else False,
            "modified": False,  # sempre False: nunca alteramos volume
        }

    def get_process_peak(self, process_name: str) -> float:
        try:
            for session in self._find_sessions(process_name):
                meter = session._ctl.QueryInterface(IAudioMeterInformation)
                return meter.GetPeakValue()
        except Exception as e:
            self.logger.error(f"Erro ao obter pico de '{process_name}': {e}")
        return -1.0

    def get_master_peak(self, device_name: str = "RADIO") -> float:
        """Retorna o pico master do dispositivo (somente leitura). Thread-safe."""
        with self._lock:
            try:
                try:
                    comtypes.CoInitialize()
                except Exception:
                    pass

                if self._cached_meter and self._cached_device_name == device_name:
                    try:
                        return self._cached_meter.GetPeakValue()
                    except Exception:
                        self._cached_meter = None

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

                if not self._cached_meter:
                    interface = self._cached_device._dev.Activate(
                        IAudioMeterInformation._iid_, comtypes.CLSCTX_ALL, None
                    )
                    self._cached_meter = interface.QueryInterface(IAudioMeterInformation)

                return self._cached_meter.GetPeakValue()

            except Exception as e:
                self.logger.error(f"Erro ao obter pico master do dispositivo '{device_name}': {e}")
                self._cached_meter = None
                self._cached_device = None
                return -1.0
            finally:
                try:
                    comtypes.CoUninitialize()
                except Exception:
                    pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    am = AudioManager()
    print(f"Master Peak: {am.get_master_peak('RADIO')}")
