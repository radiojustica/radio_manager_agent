import os
import sys
from pywinauto import Desktop
import psutil

def deep_inspect():
    print("Iniciando inspeção profunda...")
    windows = Desktop(backend="win32").windows()
    zara = None
    for w in windows:
        try:
            if "zararadio.exe" in psutil.Process(w.process_id()).name().lower() and w.is_visible():
                zara = w
                break
        except: continue
    
    if not zara:
        print("ZaraRadio não encontrado.")
        return

    print(f"Janela: {zara.window_text()}")
    
    # List all descendants with details
    count = 0
    for child in zara.descendants():
        try:
            name = child.window_text()
            class_name = child.class_name()
            enabled = child.is_enabled()
            visible = child.is_visible()
            rect = child.rectangle()
            print(f"Index: {count} | Class: {class_name} | Enabled: {enabled} | Visible: {visible} | Rect: {rect} | Text: '{name}'")
            count += 1
        except: continue

if __name__ == "__main__":
    deep_inspect()


