from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
import comtypes

def list_all_output_devices():
    print("--- Listando Dispositivos de Saída ---")
    devices = AudioUtilities.GetAllDevices()
    for device in devices:
        try:
            # Check if it's an output device (Render)
            # and print its name
            name = device.FriendlyName
            print(f"Device: {name}")
            
            # Try to get peak to see if it works for this device
            try:
                interface = device.Activate(IAudioMeterInformation._iid_, comtypes.CLSCTX_ALL, None)
                meter = interface.QueryInterface(IAudioMeterInformation)
                print(f"  > Pico Atual: {meter.GetPeakValue():.4f}")
            except:
                print("  > (Não suporta medição de pico ou não é saída)")
        except: continue

if __name__ == "__main__":
    list_all_output_devices()


