from pywinauto import Desktop
from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
import psutil

def check_all_audio():
    from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
    print("--- Sessões de Áudio Detectadas ---")
    try:
        sessions = AudioUtilities.GetAllSessions()
        for session in sessions:
            try:
                name = "Unknown"
                if session.Process:
                    name = session.Process.name()
                elif session.Identifier:
                    name = session.Identifier
                
                meter = session._ctl.QueryInterface(IAudioMeterInformation)
                peak = meter.GetPeakValue()
                print(f"Processo: {name} | Pico: {peak:.4f}")
            except: continue
    except Exception as e:
        print(f"Erro ao ler sessões: {e}")

    print("\n--- Pico do Dispositivo Padrão ---")
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioMeterInformation._iid_, 1, None)
        meter = interface.QueryInterface(IAudioMeterInformation)
        print(f"Pico Geral (Master): {meter.GetPeakValue():.4f}")
    except Exception as e:
        print(f"Erro ao ler Master: {e}")

if __name__ == "__main__":
    check_all_audio()


