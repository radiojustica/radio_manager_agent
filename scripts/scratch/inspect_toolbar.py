import os
import sys
from pywinauto import Desktop
import psutil

def inspect_toolbar():
    print("Iniciando inspeção da Toolbar...")
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

    # Find ALL toolbars
    toolbars = [c for c in zara.descendants() if c.class_name() == "ToolbarWindow32"]
    
    if not toolbars:
        print("Nenhuma Toolbar encontrada.")
        return

    print(f"Total de Toolbars encontradas: {len(toolbars)}")
    
    for idx, tb in enumerate(toolbars):
        print(f"--- Toolbar {idx} ---")
        try:
            count = tb.button_count()
            for i in range(count):
                try:
                    btn = tb.button(i)
                    print(f"  Button {i}: Text='{btn.text()}' | ID={btn.id()} | Enabled={btn.is_enabled()}")
                except: continue
        except: 
            print(f"  (Não foi possível ler os botões desta toolbar)")

if __name__ == "__main__":
    inspect_toolbar()


