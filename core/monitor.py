import os
import time
import json
import logging
import subprocess
import sys
import ctypes
import shutil
import win32gui
from collections import deque
from datetime import datetime
import psutil
import pywinauto
from pywinauto import Desktop

# Updated imports to point to scripts/
from scripts.reboot_blocker import RebootBlocker
from scripts.log_analyser import LogAnalyser
from scripts.audio_manager import AudioManager
from scripts.notifier import TelegramNotifier
from scripts.email_reporter import EmailReporter
from scripts.vmix_controller import VMixController
from scripts.ndi_relay import NDIRelay
from scripts.weekly_csv_generator import WeeklyCSVGenerator

# Global variables for optional RADIO module
MotorLogico = None
Config = None

# Windows Constants for messaging
WM_KEYDOWN = 0x0100
WM_KEYUP   = 0x0101
VK_P       = 0x50

# Maximum events kept in memory
MAX_DAILY_EVENTS = 200

class RadioMonitor:
    def __init__(self, config_path="config/settings.json"):
        # Resolução de caminho absoluto para o config_path quando rodando como EXE
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
            self.config_path = os.path.join(base_dir, config_path)
        else:
            self.config_path = os.path.abspath(config_path)
            
        self.load_config()
        self.setup_logging()

        # Inject PROGRAMA_MUSICAS path from settings (not hardcoded)
        programa_path = self.settings.get("paths", {}).get("programa_musicas", "")
        if programa_path and os.path.isdir(programa_path) and programa_path not in sys.path:
            sys.path.insert(0, programa_path)
            # Re-attempt import after path injection
            try:
                global MotorLogico, Config
                from RADIO import MotorLogico, Config
            except ImportError:
                pass

        self.reboot_blocker = RebootBlocker()
        self.log_analyser = LogAnalyser(self.settings)
        self.audio_manager = AudioManager(limit=0.24)

        # Initialize Notifier (Telegram/WhatsApp)
        notif_cfg = self.settings.get("notifications", {}).get("telegram", {})
        self.notifier = TelegramNotifier(notif_cfg)


        # Initialize Email Reporter
        email_cfg = self.settings.get("notifications", {}).get("email", {})
        self.email_reporter = EmailReporter(email_cfg)

        # Initialize Weekly CSV Generator
        log_dir = self.settings.get("apps", {}).get("zararadio", {}).get("log_path", r"D:\RADIO\LOG ZARARADIO")
        reports_dir = os.path.join(os.path.dirname(self.config_path), "reports")
        self.weekly_generator = WeeklyCSVGenerator(log_dir, reports_dir)

        # Initialize vMix Controller
        vmix_cfg = self.settings.get("vmix", {})
        self.vmix = VMixController(
            ip=vmix_cfg.get("ip", "172.16.217.226"),
            port=vmix_cfg.get("port", 8088)
        )
        self.live_session_active = False
        self.last_track = None

        # NDI Relay (quarantined — enable via settings when needed)
        self.ndi_relay = None
        self.stream_url = None

        # Daily history — deque is O(1) for append/pop vs list.pop(0) which is O(n)
        self.daily_events: deque = deque(maxlen=MAX_DAILY_EVENTS)
        self.last_report_date = None
        self.suspended = False  # Manual suspension flag (e.g. during NDI sessions)

    def load_config(self):
        """Loads configuration from settings.json."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            print(f"[CRITICAL] Config file not found: {self.config_path}")
            self.settings = {}
        except json.JSONDecodeError as e:
            print(f"[CRITICAL] Invalid JSON in config file: {e}")
            self.settings = {}
        except Exception as e:
            print(f"[CRITICAL] Error loading config: {e}")
            self.settings = {}

    def reload_config(self):
        """Hot-reloads configuration without restarting the agent."""
        self.logger.info("Reloading configuration from disk...")
        self.load_config()

    def setup_logging(self):
        """Sets up logging for the monitor agent."""
        log_dir = "logs"
        if getattr(sys, 'frozen', False):
            log_dir = os.path.join(os.path.dirname(sys.executable), "logs")
            
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, f"radio_agent_{datetime.now().strftime('%Y%m%d')}.log")

        # Avoid adding duplicate handlers if setup_logging is called more than once
        logger = logging.getLogger("RadioManagerAgent.Monitor")
        if not logger.handlers:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s | %(levelname)s | %(message)s',
                handlers=[
                    logging.FileHandler(log_file, encoding='utf-8'),
                    logging.StreamHandler()
                ]
            )
        self.logger = logger
        self.logger.info("Radio Manager Agent started (Core Version).")

    def log_event(self, event_type: str, message: str):
        """Logs an event to the daily history and to the logger."""
        entry = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "type": event_type,
            "message": message
        }
        self.daily_events.append(entry)
        self.logger.info(f"[EVENT:{event_type}] {message}")

    def get_current_block_hour(self) -> int:
        """Returns the start hour of the current 2-hour block."""
        hour = datetime.now().hour
        return (hour // 2) * 2

    def get_target_playlist(self) -> str:
        """Returns path to the playlist for the current block."""
        block_h = self.get_current_block_hour()
        folder = self.settings.get("paths", {}).get("programacao", r"D:\RADIO\PROGRAMACAO")
        return os.path.join(folder, f"PROG_{block_h:02d}H.m3u")

    def check_processes(self) -> dict:
        """Checks if configured applications are running via psutil."""
        apps = self.settings.get("apps", {})
        status = {}
        try:
            running_names = {p.name().lower() for p in psutil.process_iter(['name'])}
            for app_name, app_info in apps.items():
                process_name = app_info.get("process_name", "").lower()
                if process_name in running_names:
                    status[app_name] = "Running"
                else:
                    self.logger.warning(f"{app_name} ({process_name}) is NOT running!")
                    status[app_name] = "STOPPED"
        except Exception as e:
            self.logger.error(f"Error checking processes: {e}")
        return status

    def ensure_apps_running(self):
        """Ensures ZaraRadio and BUTT instances are active."""
        apps_status = self.check_processes()
        zara_set = self.settings.get("apps", {}).get("zararadio", {})

        zara_win = self.find_zara_window()
        is_hung = bool(zara_win and ctypes.windll.user32.IsHungAppWindow(zara_win.handle))

        if apps_status.get("zararadio") != "Running" or is_hung:
            reason = "FROZEN (HUNG)" if is_hung else "stopped"
            if is_hung:
                self.logger.error("ZaraRadio is FROZEN (HUNG). Killing and restarting...")
                subprocess.run("taskkill /F /IM ZaraRadio.exe /T", shell=True, capture_output=True)
                time.sleep(2)

            self.logger.info(f"Restarting ZaraRadio (reason: {reason})...")

            notif_cfg = self.settings.get("notifications", {}).get("telegram", {})
            if notif_cfg.get("notify_on_restart"):
                msg = f"ZaraRadio was {reason}. Restarting engine and forcing playback."
                self.notifier.send_alert("RESTART", {
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "message": msg
                })
                self.log_event("RESTART", msg)

            playlist = self.get_target_playlist()

            if not os.path.exists(playlist):
                self.logger.warning(f"Playlist {playlist} not found. Running emergency generation via RADIO.py...")
                if MotorLogico is not None and Config is not None:
                    try:
                        def on_success(filename):
                            nonlocal playlist
                            playlist = os.path.join(Config.PASTA_PROGRAMACAO, filename)

                        MotorLogico.gerar_bloco_extra(
                            "Ensolarado", self.logger.info, lambda v, t: None,
                            lambda m: self.logger.info(m), lambda e: self.logger.error(e),
                            on_success
                        )
                    except Exception as e:
                        self.logger.error(f"Failed to run RADIO.py generator: {e}")
                else:
                    self.logger.warning("RADIO.py module not available. Skipping emergency playlist generation.")

            executable = zara_set.get("executable_path", "")
            if not executable:
                self.logger.error("ZaraRadio executable_path not configured in settings.json!")
                return

            if os.path.exists(playlist):
                subprocess.Popen([executable, playlist])
            else:
                subprocess.Popen([executable])

            time.sleep(7)
            self.trigger_play_on_zara()

        try:
            butt_count = sum(1 for p in psutil.process_iter(['name']) if p.info['name'].lower() == 'butt.exe')
            if butt_count < 3:
                self.logger.warning(f"Only {butt_count}/3 BUTT instance(s) running.")
        except Exception as e:
            self.logger.error(f"Error counting BUTT instances: {e}")

    def find_zara_window(self):
        """Finds the actual ZaraRadio application window."""
        IGNORED_CLASSES = {"tooltips_class32", "CabinetWClass", "WorkerW"}
        try:
            windows = Desktop(backend="win32").windows()
            for w in windows:
                try:
                    if not w.is_visible(): continue
                    if w.class_name() == "wxWindowClassNR":
                        pid = w.process_id()
                        if psutil.Process(pid).name().lower() == "zararadio.exe":
                            return w
                except Exception: continue
            for w in windows:
                try:
                    if not w.is_visible() or not w.window_text(): continue
                    if w.class_name() in IGNORED_CLASSES: continue
                    pid = w.process_id()
                    if psutil.Process(pid).name().lower() == "zararadio.exe":
                        return w
                except Exception: continue
            return None
        except Exception as e:
            self.logger.debug(f"find_zara_window error: {e}")
            return None

    def is_window_hung(self, title_pattern=None) -> bool:
        app = self.find_zara_window()
        return bool(app and ctypes.windll.user32.IsHungAppWindow(app.handle))

    def get_zara_current_track(self) -> Optional[str]:
        try:
            log_dir = self.settings.get("apps", {}).get("zararadio", {}).get("log_path", "")
            current_song_file = os.path.join(log_dir, "CurrentSong.txt")
            if os.path.exists(current_song_file):
                with open(current_song_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip()
                    if content: return content

            app = self.find_zara_window()
            if app:
                title = app.window_text()
                if " - [" in title and "]" in title:
                    start = title.find("[") + 1
                    end = title.find("]")
                    return title[start:end].strip()
            return None
        except Exception as e:
            self.logger.debug(f"get_zara_current_track error: {e}")
            return None

    def trigger_play_on_zara(self) -> bool:
        try:
            app = self.find_zara_window()
            if not app: return False
            if ctypes.windll.user32.IsHungAppWindow(app.handle): return False
            hwnd = app.handle
            ctypes.windll.user32.PostMessageW(hwnd, WM_KEYDOWN, VK_P, 0)
            ctypes.windll.user32.PostMessageW(hwnd, WM_KEYUP,   VK_P, 0)
            self.logger.info(f"Triggered PLAY (P) on: {app.window_text()}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to trigger PLAY: {e}")
            return False

    def is_zara_playing(self) -> bool:
        PLAY_INDICATORS = ["Reproduzindo", "Playing", "Tempo restante", "Remaining time", "NO AR"]
        TITLE_INDICATORS = ["[Playing]", "[Reproduzindo]", "[Reproducing]"]
        try:
            desktop = pywinauto.Desktop(backend="win32")
            zara_windows = [w for w in desktop.windows() if w.class_name() == "wxWindowClassNR"]
            if not zara_windows:
                zara_windows = [w for w in desktop.windows() if "ZaraRadio" in w.window_text()]
            if not zara_windows: return False
            for w in zara_windows:
                title = w.window_text()
                if any(ind in title for ind in TITLE_INDICATORS): return True
                for child in w.descendants():
                    text = child.window_text()
                    if any(ind in text for ind in PLAY_INDICATORS): return True
            return False
        except Exception as e:
            self.logger.error(f"Error checking ZaraRadio playback status: {e}")
            return False

    def ensure_butt_connected(self):
        try:
            windows = Desktop(backend="win32").windows()
            for w in windows:
                try:
                    title = w.window_text()
                    if "butt " in title.lower() and "connected" not in title.lower():
                        self.logger.warning(f"BUTT instance '{title}' is IDLE. Forcing Connect (Ctrl+C)...")
                        w.type_keys('^c', set_foreground=False)
                except Exception: continue
        except Exception as e:
            self.logger.error(f"Error in BUTT reconnect: {e}")

    def quarantine_file(self, file_path: str, reason: str):
        quarantine_dir = self.settings.get("grade", {}).get("pasta_quarentena", r"D:\RADIO\QUARENTENA_TJ")
        os.makedirs(quarantine_dir, exist_ok=True)
        if not os.path.exists(file_path): return
        filename = os.path.basename(file_path)
        dest_path = os.path.join(quarantine_dir, filename)
        try:
            if os.path.exists(dest_path):
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                dest_path = os.path.join(quarantine_dir, f"{ts}_{filename}")
            shutil.move(file_path, dest_path)
            self.logger.warning(f"☣️ FILE QUARANTINED: {filename} (Reason: {reason})")
            audit_log = os.path.join(quarantine_dir, "audit_quarentena.log")
            ts_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(audit_log, "a", encoding="utf-8") as f:
                f.write(f"[{ts_now}] ARQUIVO: {filename} | ORIGEM: {file_path} | MOTIVO: {reason}\n")
            msg = f"☣️ *ARQUIVO EM QUARENTENA*\n\n*Arquivo:* {filename}\n*Motivo:* {reason}"
            self.notifier.send_alert("QUARANTINE", {"time": ts_now, "message": msg})
            self.log_event("QUARANTINE", f"File moved to quarantine: {filename}")
        except Exception as e:
            self.logger.error(f"Failed to quarantine file {file_path}: {e}")

    def check_playback_activity(self) -> bool:
        try:
            log_file = self.log_analyser.get_latest_log("zararadio")
            if not log_file: return True
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = [l.strip() for l in f if l.strip()]
            if not lines: return True
            last_line = lines[-1]
            parts = last_line.split('\t')
            if len(parts) >= 2:
                entry_type = parts[1].strip().lower()
                if 'erro' in entry_type:
                    if len(parts) >= 3:
                        file_path = parts[2].strip()
                        self.quarantine_file(file_path, f"ZaraRadio Playback Error: {last_line}")
                    return False
                if 'inicio' in entry_type or 'fim' in entry_type: return True
            return True
        except Exception as e:
            self.logger.error(f"Error reading ZaraRadio log: {e}")
            return True

    def check_system_health(self) -> dict:
        metrics = {}
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            vm = psutil.virtual_memory()
            metrics["cpu_percent"] = cpu_percent
            metrics["ram_percent"] = vm.percent
            metrics["ram_kb_free"] = vm.available // 1024
            cpu_threshold = self.settings.get("monitoring", {}).get("cpu_threshold", 90)
            ram_threshold = self.settings.get("monitoring", {}).get("ram_threshold", 95)
            if cpu_percent >= cpu_threshold: self.log_event("WARNING", f"CPU usage critical: {cpu_percent:.1f}%")
            if vm.percent >= ram_threshold: self.log_event("WARNING", f"RAM usage critical: {vm.percent:.1f}%")
        except Exception as e:
            self.logger.error(f"Error checking system health: {e}")
        return metrics

    def manage_tasks(self):
        forbidden = self.settings.get("monitoring", {}).get("forbidden_tasks", [])
        for task in forbidden:
            try:
                check_result = subprocess.run(f'schtasks /Query /TN "{task}" /FO LIST', shell=True, capture_output=True, text=True, encoding='latin1')
                if check_result.returncode != 0: continue
                self.logger.warning(f"⚠️  Forbidden task '{task}' found! DELETING...")
                delete_result = subprocess.run(f'schtasks /delete /tn "{task}" /f', shell=True, capture_output=True, text=True, encoding='latin1')
                if delete_result.returncode == 0: self.log_event("TASK_DELETED", f"Scheduled task '{task}' was deleted.")
            except Exception as e: self.logger.error(f"Exception while managing task '{task}': {e}")

    def run_cycle(self):
        self.logger.info("--- Monitoring Cycle START ---")
        reboot_settings = self.settings.get("reboot_prevention", {})
        self.ensure_apps_running()
        self.ensure_butt_connected()
        process_status = self.check_processes()
        if not self.suspended and not self.live_session_active:
            is_active = self.check_playback_activity()
            if not is_active and process_status.get("zararadio") == "Running":
                self.trigger_play_on_zara()
        self.audio_manager.limit_app_volume("ZaraRadio.exe")
        self.manage_tasks()
        health = self.check_system_health()
        self.reboot_blocker.prevent_sleep()
        if reboot_settings.get("abort_shutdown_periodically"): self.reboot_blocker.abort_shutdown()
        self.logger.info("--- Monitoring Cycle END ---")

    def check_and_send_daily_report(self):
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        report_time_str = self.settings.get("notifications", {}).get("email", {}).get("report_time", "07:00")
        try: report_hour, report_minute = map(int, report_time_str.split(":"))
        except ValueError: report_hour, report_minute = 7, 0
        if now.hour == report_hour and now.minute == report_minute and self.last_report_date != current_date:
            summary = {
                "zara_status": "ONLINE" if self.check_processes().get("zararadio") == "Running" else "OFFLINE",
                "butt_count": sum(1 for p in psutil.process_iter(['name']) if p.info['name'].lower() == 'butt.exe'),
                "restarts": sum(1 for e in self.daily_events if e['type'] == 'RESTART'),
                "events": list(self.daily_events)
            }
            attachment = self.weekly_generator.generate_report(7) if now.weekday() == 0 else None
            if self.email_reporter.send_daily_report(summary, attachment_path=attachment):
                self.last_report_date = current_date
                self.daily_events.clear()

    def check_vmix_and_switch(self):
        is_live, title = self.vmix.is_session_live()
        if is_live and not self.live_session_active:
            self.live_session_active = True
            self.audio_manager.limit_app_volume("ZaraRadio.exe", limit=0.0)
            self.audio_manager.limit_app_volume("NDI Monitor.exe", limit=1.0)
            self.log_event("LIVE_START", f"Live session started: {title}")
        elif not is_live and self.live_session_active:
            self.live_session_active = False
            self.audio_manager.limit_app_volume("ZaraRadio.exe", limit=0.24)
            self.trigger_play_on_zara()
            self.audio_manager.limit_app_volume("NDI Monitor.exe", limit=0.0)
            self.log_event("LIVE_END", "Live session ended.")

    def check_zara_track_and_trigger_vmix(self):
        vmix_cfg = self.settings.get("vmix", {})
        if not vmix_cfg.get("enabled", False): return
        current_track = self.get_zara_current_track()
        if not current_track or current_track == self.last_track: return
        self.last_track = current_track
        triggers = vmix_cfg.get("track_triggers", {})
        for kw, action in triggers.items():
            if kw.upper() in current_track.upper():
                self.vmix.send_command(function=action.get("function", "Cut"), input_name=action.get("input"))
                break

    def check_ndi_session(self):
        ndi_active = False
        def callback(hwnd, extra):
            nonlocal ndi_active
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                if any(k in title for k in ("ndi monitor", "plenário", "plenario", "sessão", "sessao")): ndi_active = True
        try: win32gui.EnumWindows(callback, None)
        except: pass
        if ndi_active and not self.suspended: self.suspended = True
        elif not ndi_active and self.suspended: self.suspended = False

    def run(self):
        interval = self.settings.get("monitoring", {}).get("interval_seconds", 60)
        self.reboot_blocker.prevent_sleep()
        self.reboot_blocker.apply_registry_blocks()
        last_cycle_time = 0
        while True:
            try:
                now = time.time()
                if now - last_cycle_time >= interval:
                    if not self.live_session_active: self.run_cycle()
                    self.check_and_send_daily_report()
                    last_cycle_time = now
                self.check_vmix_and_switch()
                self.check_ndi_session()
                self.check_zara_track_and_trigger_vmix()
            except Exception as e: self.logger.critical(f"Unhandled exception: {e}", exc_info=True)
            time.sleep(1)

if __name__ == "__main__":
    RadioMonitor().run()
