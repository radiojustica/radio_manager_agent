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

    def get_master_peak(self, device_name: str = "INTERNO") -> float:
        """Retorna o pico master do dispositivo de transmissão (somente leitura).

        No TJRN a placa de transmissão é USB e aparece com nomes como
        'RADIO (USB Audio CODEC )' e/ou 'INTERNO (2- USB Audio CODEC )'.
        Como só uma delas efetivamente carrega o áudio ao vivo, varremos todas
        as que casam com as keywords e retornamos o MAIOR pico (o dispositivo ativo).
        """
        DEVICE_KEYWORDS = ["usb audio codec", "interno", "codec"]
        with self._lock:
            try:
                try:
                    comtypes.CoInitialize()
                except Exception:
                    pass

                devices = AudioUtilities.GetAllDevices()
                candidates = []
                for d in devices:
                    try:
                        fn = d.FriendlyName.lower()
                    except Exception:
                        continue
                    if any(k in fn for k in DEVICE_KEYWORDS):
                        candidates.append(d)

                if not candidates:
                    candidates = [AudioUtilities.GetSpeakers()]

                best_peak = -1.0
                for dev in candidates:
                    try:
                        interface = dev._dev.Activate(
                            IAudioMeterInformation._iid_, comtypes.CLSCTX_ALL, None
                        )
                        meter = interface.QueryInterface(IAudioMeterInformation)
                        p = meter.GetPeakValue()
                        if p > best_peak:
                            best_peak = p
                    except Exception:
                        continue
                return best_peak

            except Exception as e:
                self.logger.error(f"Erro ao obter pico master: {e}")
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
