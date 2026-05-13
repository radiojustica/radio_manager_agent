import ctypes
import os
import sys
import win32api
import win32event
import winerror
from pathlib import Path

# Variável global para manter o handle do mutex vivo
_instance_mutex = None

def is_admin():
    """Verifica se o processo atual possui privilégios de administrador."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def verificar_instancia_unica():
    """Garante que apenas uma instância rode usando Mutex do Windows."""
    global _instance_mutex
    mutex_name = "Global\\OmniCoreV2_Master_Mutex_Lock"
    
    try:
        _instance_mutex = win32event.CreateMutex(None, False, mutex_name)
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            print("OmniCoreV2: Já existe uma instância ativa. Saindo...")
            return False
        return True
    except Exception as e:
        print(f"Erro Mutex: {e}")
        return True

def run_as_admin() -> bool:
    """
    Reinicia o script atual com privilégios elevados.
    Retorna True se conseguiu elevar, False caso contrário.
    """
    script = sys.argv[0]
    params = " ".join(sys.argv[1:])
    try:
        result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            f'"{script}" {params}',
            os.getcwd(),
            1
        )
        # ShellExecuteW retorna > 32 se bem-sucedido
        if result > 32:
            return True
        else:
            print(f"Falha ao solicitar elevação: código {result}")
            return False
    except Exception as e:
        print(f"Falha ao solicitar elevação: {e}")
        return False