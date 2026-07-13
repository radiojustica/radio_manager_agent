import os
import sys
from pywinauto import Desktop
import psutil

def inspect_zara():
    print("Buscando ZaraRadio...")
    windows = Desktop(backend="win32").windows()
    zara = None
    for w in windows:
        try:
            if "zararadio.exe" in psutil.Process(w.process_id()).name().lower() and w.is_visible():
                zara = w
                break
        except: continue
    
    if not zara:
        print("ZaraRadio não encontrado aberto.")
        return

    print(f"Janela encontrada: {zara.window_text()}")
    print("--- Analisando botões de controle ---")
    
    # Try to find common control IDs or names for Play/Stop
    # In ZaraRadio, they are often in a Toolbar or just named buttons
    for child in zara.descendants():
        try:
            name = child.window_text()
            class_name = child.class_name()
            if name or "Button" in class_name:
                enabled = child.is_enabled()
                print(f"Control: '{name}' | Class: {class_name} | Enabled: {enabled}")
        except: continue

if __name__ == "__main__":
    inspect_zara()


