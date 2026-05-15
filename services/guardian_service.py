import os
import time
import ctypes
import subprocess
import psutil
import logging
import threading
import win32gui
import win32con
import win32api
import win32process
from datetime import datetime
from typing import Optional

# Import the original monitor logic to preserve all features
from core.monitor import RadioMonitor

class GuardianService(RadioMonitor):
    """
    Advanced Guardian Service that merges the high-reliability automation
    of Omni Core with the comprehensive monitoring features of Radio Guardian Agent.
    """
    def __init__(self, config_path="config/settings.json"):
        super().__init__(config_path)
        # Ensure events list is available for the status API
        self.events_list = []
        
        # MODO FREEZE: Desativar alertas externos para foco em logs locais
        notifications = self.settings.get("notifications", {})
        if "telegram" in notifications:
            notifications["telegram"]["enabled"] = False
        if "email" in notifications:
            notifications["email"]["enabled"] = False

    def log_event(self, event_type: str, message: Optional[str] = None):
        """Unified logging that updates both the terminal and the events list."""
        # If only one argument provided, treat as message
        if message is None:
            message = event_type
            event_type = "INFO"
        
        super().log_event(event_type, message)
        
        # Keep events list updated for API consumption
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.events_list.insert(0, {"time": timestamp, "type": event_type, "message": message})
        if len(self.events_list) > 100:
            self.events_list.pop()

    @property
    def events(self):
        """Web-compatible property for accessing history."""
        return self.events_list

    def force_play(self) -> bool:
        """
        Forces play command on ZaraRadio using the 'P' key.
        Uses Thread Attachment for high reliability.
        """
        self.log_event("ACTION", "Forçando Play (P) no ZaraRadio via Thread Sync.")
        return self.trigger_play_on_zara()

    def restart_zara(self):
        """
        Protocolo de reinicialização inteligente do ZaraRadio.
        Mata o processo e reinicia com a playlist do bloco atual.
        """
        self.log_event("SYSTEM", "Acionando reinicialização programada do ZaraRadio.")
        try:
            subprocess.run(["taskkill", "/F", "/IM", "ZaraRadio.exe", "/T"], capture_output=True, text=True, timeout=5)
            time.sleep(2)
        except: pass

        playlist = self.get_target_playlist()
        executable = self.settings.get("apps", {}).get("zararadio", {}).get("executable_path", r"D:\ZaraRadio\ZaraRadio.exe")
        
        cmd = [executable]
        if os.path.exists(playlist):
            cmd.append(playlist)
            self.log_event("SYSTEM", f"Iniciando Zara com playlist: {os.path.basename(playlist)}")
        else:
            self.log_event("WARNING", "Playlist do bloco não encontrada para restart.")

        try:
            subprocess.Popen(cmd, shell=False)
            time.sleep(5)
            self.force_play()
        except Exception as e:
            self.log_event("ERROR", f"Falha ao reiniciar ZaraRadio: {e}")

    def reconnect_idle_butts(self):
        """
        Varre instâncias do BUTT e tenta reconectar usando injeção de teclas Ctrl+C.
        """
        try:
            # We use the analyzer from the status router to find PIDs
            from routers.status import analisar_instancias_butt
            instancias = analisar_instancias_butt()
            reconectados = 0
            for b in instancias:
                if b['status'] in ('parado', 'desconectado'):
                    self.log_event("BUTT", f"Tentando reconectar BUTT (PID {b['pid']})...")
                    if self._send_command_to_butt(b['pid'], 'ctrl+c'):
                        reconectados += 1
                        time.sleep(1)
            return reconectados, len(instancias)
        except Exception as e:
            self.log_event("ERROR", f"Erro na reconexão automática de BUTTs: {e}")
            return 0, 0

    def _send_command_to_butt(self, pid: int, key_combination: str = 'ctrl+c') -> bool:
        """Injeta atalhos de teclado em janelas do BUTT sem roubar o foco."""
        vk_map = {
            'ctrl': win32con.VK_CONTROL, 'alt': win32con.VK_MENU,
            'shift': win32con.VK_SHIFT, 'c': ord('C'), 
            'p': ord('P'), 'r': ord('R')
        }
        parts = key_combination.lower().split('+')
        modifiers = [p for p in parts if p in ('ctrl', 'alt', 'shift')]
        main_key = parts[-1]
        vk_main = vk_map.get(main_key)
        
        if not vk_main: return False

        curr_thread = win32api.GetCurrentThreadId()
        target_thread = None

        try:
            def enum_callback(h, l):
                if win32gui.IsWindowVisible(h):
                    _, found_pid = win32process.GetWindowThreadProcessId(h)
                    if found_pid == pid: l.append(h)
            
            hwnds = []
            win32gui.EnumWindows(enum_callback, hwnds)
            if not hwnds: return False
            hwnd = hwnds[0]

            target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)
            ctypes.windll.user32.AttachThreadInput(curr_thread, target_thread, True)
            
            # State management
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            for mod in modifiers: win32api.keybd_event(vk_map[mod], 0, 0, 0)
            win32api.keybd_event(vk_main, 0, 0, 0)
            time.sleep(0.1)
            win32api.keybd_event(vk_main, 0, win32con.KEYEVENTF_KEYUP, 0)
            for mod in reversed(modifiers): win32api.keybd_event(vk_map[mod], 0, win32con.KEYEVENTF_KEYUP, 0)

            return True
        except: return False
        finally:
            if target_thread:
                ctypes.windll.user32.AttachThreadInput(curr_thread, target_thread, False)

    def disable_weekly_reboot_task(self) -> bool:
        """Garante que as tarefas legadas ou de reboot estejam desabilitadas."""
        tasks_to_block = [r"\Reiniciar computadores semanalmente", r"\RADIO"]
        
        all_ok = True
        for task_uri in tasks_to_block:
            self.log_event("BLOCKER", f"Verificando tarefa: {task_uri}")
            try:
                cmd = ['schtasks', '/Change', '/TN', task_uri, '/Disable']
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding='cp1252',
                    errors='replace',
                    timeout=15
                )

                if result.returncode == 0:
                    self.log_event("BLOCKER", f"Tarefa '{task_uri}' desabilitada com sucesso.")
                else:
                    stderr = result.stderr.strip()
                    if "DISABLED" in stderr.upper() or "NOT FOUND" in stderr.upper():
                        self.log_event("BLOCKER", f"Tarefa '{task_uri}' já inativa ou inexistente.")
                    else:
                        self.log_event("WARNING", f"Falha ao desabilitar '{task_uri}': {stderr}")
                        all_ok = False
            except Exception as e:
                self.log_event("ERROR", f"Erro ao processar blocker para {task_uri}: {e}")
                all_ok = False
        return all_ok


# Singleton global para uso em todo o backend e frontend GUI
guardian_instance = GuardianService()


