import os
import time
import json
import logging
import subprocess
import sys
import ctypes
import shutil
import win32gui # Adicionado para detecção de janelas
from collections import deque
from datetime import datetime
from .reboot_blocker import RebootBlocker
from .log_analyser import LogAnalyser
from .audio_manager import AudioManager
import pywinauto
from pywinauto import Desktop
from pywinauto.keyboard import send_keys
from .notifier import TelegramNotifier
from .email_reporter import EmailReporter
from .vmix_controller import VMixController
from .ndi_relay import NDIRelay
from .weekly_csv_generator import WeeklyCSVGenerator
import psutil

# ... (restante das constantes)

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

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

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
        self.logger.info("Radio Manager Agent started.")

    def log_event(self, event_type: str, message: str):
        """Logs an event to the daily history and to the logger."""
        entry = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "type": event_type,
            "message": message
        }
        self.daily_events.append(entry)
        self.logger.info(f"[EVENT:{event_type}] {message}")

    # ------------------------------------------------------------------
    # Playlist helpers
    # ------------------------------------------------------------------

    def get_current_block_hour(self) -> int:
        """Returns the start hour of the current 2-hour block."""
        hour = datetime.now().hour
        return (hour // 2) * 2

    def get_target_playlist(self) -> str:
        """Returns path to the playlist for the current block."""
        block_h = self.get_current_block_hour()
        folder = self.settings.get("paths", {}).get("programacao", r"D:\RADIO\PROGRAMACAO")
        return os.path.join(folder, f"PROG_{block_h:02d}H.m3u")

    # ------------------------------------------------------------------
    # Process management
    # ------------------------------------------------------------------

    def check_processes(self) -> dict:
        """Checks if configured applications are running via psutil (faster than tasklist)."""
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

        # 1. Start ZaraRadio if not found or HUNG
        zara_win = self.find_zara_window()
        is_hung = bool(zara_win and ctypes.windll.user32.IsHungAppWindow(zara_win.handle))

        if apps_status.get("zararadio") != "Running" or is_hung:
            reason = "FROZEN (HUNG)" if is_hung else "stopped"
            if is_hung:
                self.logger.error("ZaraRadio is FROZEN (HUNG). Killing and restarting...")
                subprocess.run(
                    "taskkill /F /IM ZaraRadio.exe /T",
                    shell=True, capture_output=True
                )
                time.sleep(2)

            self.logger.info(f"Restarting ZaraRadio (reason: {reason})...")

            # Send Telegram Alert
            notif_cfg = self.settings.get("notifications", {}).get("telegram", {})
            if notif_cfg.get("notify_on_restart"):
                msg = f"ZaraRadio was {reason}. Restarting engine and forcing playback."
                self.notifier.send_alert("RESTART", {
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "message": msg
                })
                self.log_event("RESTART", msg)

            playlist = self.get_target_playlist()

            # If playlist is missing, use the "Expert" logic from RADIO.py
            if not os.path.exists(playlist):
                self.logger.warning(
                    f"Playlist {playlist} not found. Running emergency generation via RADIO.py..."
                )
                if MotorLogico is not None and Config is not None:
                    try:
                        def on_success(filename):
                            nonlocal playlist
                            playlist = os.path.join(Config.PASTA_PROGRAMACAO, filename)

                        MotorLogico.gerar_bloco_extra(
                            "Ensolarado",
                            self.logger.info,
                            lambda v, t: None,
                            lambda m: self.logger.info(m),
                            lambda e: self.logger.error(e),
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

            time.sleep(7)  # Wait for ZaraRadio to fully initialize
            self.trigger_play_on_zara()

        # 2. Check BUTT instances
        try:
            butt_count = sum(
                1 for p in psutil.process_iter(['name'])
                if p.info['name'].lower() == 'butt.exe'
            )
            if butt_count < 3:
                self.logger.warning(
                    f"Only {butt_count}/3 BUTT instance(s) running. "
                    "Manual intervention may be required (each instance needs its own config)."
                )
        except Exception as e:
            self.logger.error(f"Error counting BUTT instances: {e}")

    # ------------------------------------------------------------------
    # ZaraRadio window helpers
    # ------------------------------------------------------------------

    def find_zara_window(self):
        """Finds the actual ZaraRadio application window, ignoring ToolTips and Explorer windows."""
        IGNORED_CLASSES = {"tooltips_class32", "CabinetWClass", "WorkerW"}
        try:
            windows = Desktop(backend="win32").windows()

            # Primary: match by wx class name + process name (most reliable)
            for w in windows:
                try:
                    if not w.is_visible():
                        continue
                    if w.class_name() == "wxWindowClassNR":
                        pid = w.process_id()
                        if psutil.Process(pid).name().lower() == "zararadio.exe":
                            return w
                except Exception:
                    continue

            # Fallback: match by process name, excluding known noise classes
            for w in windows:
                try:
                    if not w.is_visible() or not w.window_text():
                        continue
                    if w.class_name() in IGNORED_CLASSES:
                        continue
                    pid = w.process_id()
                    if psutil.Process(pid).name().lower() == "zararadio.exe":
                        return w
                except Exception:
                    continue

            return None
        except Exception as e:
            self.logger.debug(f"find_zara_window error: {e}")
            return None

    def is_window_hung(self, title_pattern=None) -> bool:
        """Checks if the ZaraRadio window is unresponsive."""
        try:
            app = self.find_zara_window()
            if app:
                return bool(ctypes.windll.user32.IsHungAppWindow(app.handle))
            return False
        except Exception as e:
            self.logger.debug(f"is_window_hung error: {e}")
            return False

    def get_zara_current_track(self) -> Optional[str]:
        """Extracts the current playing track name from ZaraRadio CurrentSong.txt or window title."""
        try:
            # 1. Try CurrentSong.txt (more reliable)
            log_dir = self.settings.get("apps", {}).get("zararadio", {}).get("log_path", "")
            current_song_file = os.path.join(log_dir, "CurrentSong.txt")
            if os.path.exists(current_song_file):
                with open(current_song_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip()
                    if content:
                        return content

            # 2. Fallback to Window Title
            app = self.find_zara_window()
            if app:
                title = app.window_text()
                # Expected formats: 
                # "ZaraRadio - [Artist - Title]"
                # "ZaraRadio - [Title]"
                if " - [" in title and "]" in title:
                    start = title.find("[") + 1
                    end = title.find("]")
                    return title[start:end].strip()
            return None
        except Exception as e:
            self.logger.debug(f"get_zara_current_track error: {e}")
            return None

    def trigger_play_on_zara(self) -> bool:
        """Sends 'P' key to ZaraRadio via PostMessage (no focus steal)."""
        try:
            app = self.find_zara_window()
            if not app:
                self.logger.warning("ZaraRadio window not found to trigger PLAY.")
                return False

            if ctypes.windll.user32.IsHungAppWindow(app.handle):
                self.logger.error("ZaraRadio is HUNG. Restart needed before triggering PLAY.")
                return False

            hwnd = app.handle
            ctypes.windll.user32.PostMessageW(hwnd, WM_KEYDOWN, VK_P, 0)
            ctypes.windll.user32.PostMessageW(hwnd, WM_KEYUP,   VK_P, 0)

            self.logger.info(f"Triggered PLAY (P via PostMessage) on: {app.window_text()}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to trigger PLAY: {e}")
            return False

    def is_zara_playing(self) -> bool:
        """Analyzes ZaraRadio UI elements to determine if it's actively playing."""
        PLAY_INDICATORS = [
            "Reproduzindo", "Playing", "Tempo restante",
            "Remaining time", "NO AR"
        ]
        TITLE_INDICATORS = ["[Playing]", "[Reproduzindo]", "[Reproducing]"]
        try:
            desktop = pywinauto.Desktop(backend="win32")
            zara_windows = [w for w in desktop.windows() if w.class_name() == "wxWindowClassNR"]

            if not zara_windows:
                # Fallback to title search
                zara_windows = [w for w in desktop.windows() if "ZaraRadio" in w.window_text()]

            if not zara_windows:
                self.logger.warning("ZaraRadio window not found for playback check.")
                return False

            for w in zara_windows:
                title = w.window_text()
                if any(ind in title for ind in TITLE_INDICATORS):
                    return True
                for child in w.descendants():
                    text = child.window_text()
                    if any(ind in text for ind in PLAY_INDICATORS):
                        return True

            return False
        except Exception as e:
            self.logger.error(f"Error checking ZaraRadio playback status: {e}")
            return False

    def ensure_butt_connected(self):
        """Finds all BUTT instances and triggers Connect (Ctrl+C) on disconnected ones."""
        try:
            windows = Desktop(backend="win32").windows()
            for w in windows:
                try:
                    title = w.window_text()
                    if "butt " in title.lower() and "connected" not in title.lower():
                        self.logger.warning(
                            f"BUTT instance '{title}' is IDLE. Forcing Connect (Ctrl+C)..."
                        )
                        w.type_keys('^c', set_foreground=False)
                except Exception:
                    continue
        except Exception as e:
            self.logger.error(f"Error in BUTT reconnect: {e}")

    def quarantine_file(self, file_path: str, reason: str):
        """Moves a problematic file to the quarantine folder and notifies via Telegram."""
        quarantine_dir = self.settings.get("grade", {}).get("pasta_quarentena", r"D:\RADIO\QUARENTENA_TJ")
        os.makedirs(quarantine_dir, exist_ok=True)

        if not os.path.exists(file_path):
            self.logger.warning(f"Cannot quarantine file (not found): {file_path}")
            return

        filename = os.path.basename(file_path)
        dest_path = os.path.join(quarantine_dir, filename)

        try:
            # Check if destination already exists (append timestamp if so)
            if os.path.exists(dest_path):
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                dest_path = os.path.join(quarantine_dir, f"{ts}_{filename}")

            shutil.move(file_path, dest_path)
            self.logger.warning(f"☣️ FILE QUARANTINED: {filename} (Reason: {reason})")
            
            # Audit log in quarantine folder
            audit_log = os.path.join(quarantine_dir, "audit_quarentena.log")
            ts_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(audit_log, "a", encoding="utf-8") as f:
                f.write(f"[{ts_now}] ARQUIVO: {filename} | ORIGEM: {file_path} | MOTIVO: {reason}\n")

            # Telegram Notification
            msg = f"☣️ *ARQUIVO EM QUARENTENA*\n\n*Arquivo:* {filename}\n*Motivo:* {reason}"
            self.notifier.send_alert("QUARANTINE", {
                "time": ts_now,
                "message": msg
            })
            self.log_event("QUARANTINE", f"File moved to quarantine: {filename}")

        except Exception as e:
            self.logger.error(f"Failed to quarantine file {file_path}: {e}")

    # ------------------------------------------------------------------
    # Playback activity check
    # ------------------------------------------------------------------

    def check_playback_activity(self) -> bool:
        """Verifies ZaraRadio status by reading the last entry in its log file.

        Logic:
        - Last entry is 'inicio' (track started) -> Radio is active, do NOT interfere.
        - Last entry is 'erro' (error)            -> Radio had a problem, may need intervention.
        - Log doesn't exist or is unreadable      -> Be conservative, do NOT force play.

        This correctly handles:
        - Long programs (1h+): last entry stays 'inicio', no interference.
        - NDI sessions: ZaraRadio intentionally paused, last entry is 'inicio', no interference.
        - Crashed radio: ZaraRadio logs 'erro', agent triggers play.
        """
        try:
            log_file = self.log_analyser.get_latest_log("zararadio")
            if not log_file:
                self.logger.warning("ZaraRadio log not found. Being conservative — assuming active.")
                return True

            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = [l.strip() for l in f if l.strip()]

            if not lines:
                return True  # Empty log — be conservative

            last_line = lines[-1]
            self.logger.debug(f"Last ZaraRadio log entry: {last_line}")

            # ZaraRadio log format: HH:MM:SS \t tipo \t arquivo
            parts = last_line.split('\t')
            if len(parts) >= 2:
                entry_type = parts[1].strip().lower()

                if 'erro' in entry_type:
                    self.logger.warning(f"ZaraRadio log shows ERROR: {last_line}")
                    
                    # QUARANTINE LOGIC: Extract path and move
                    if len(parts) >= 3:
                        file_path = parts[2].strip()
                        self.quarantine_file(file_path, f"ZaraRadio Playback Error: {last_line}")

                    return False  # Error detected -> trigger play

                if 'inicio' in entry_type or 'fim' in entry_type:
                    return True  # Track started/ended normally -> radio is active

            # Unknown format: be conservative
            return True

        except Exception as e:
            self.logger.error(f"Error reading ZaraRadio log: {e}")
            return True  # On error, be conservative: don't force play

    # ------------------------------------------------------------------
    # System health
    # ------------------------------------------------------------------

    def check_system_health(self) -> dict:
        """Monitors CPU and RAM using psutil (cross-platform, no subprocess overhead)."""
        metrics = {}
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            vm = psutil.virtual_memory()
            metrics["cpu_percent"] = cpu_percent
            metrics["ram_percent"] = vm.percent
            metrics["ram_kb_free"] = vm.available // 1024

            cpu_threshold = self.settings.get("monitoring", {}).get("cpu_threshold", 90)
            ram_threshold = self.settings.get("monitoring", {}).get("ram_threshold", 95)

            if cpu_percent >= cpu_threshold:
                self.logger.warning(f"HIGH CPU: {cpu_percent:.1f}% (threshold: {cpu_threshold}%)")
                self.log_event("WARNING", f"CPU usage critical: {cpu_percent:.1f}%")

            if vm.percent >= ram_threshold:
                self.logger.warning(f"HIGH RAM: {vm.percent:.1f}% used (threshold: {ram_threshold}%)")
                self.log_event("WARNING", f"RAM usage critical: {vm.percent:.1f}%")

        except Exception as e:
            self.logger.error(f"Error checking system health: {e}")
        return metrics

    # ------------------------------------------------------------------
    # Task management
    # ------------------------------------------------------------------

    def manage_tasks(self):
        """Disables/deletes scheduled tasks listed in the forbidden_tasks list."""
        forbidden = self.settings.get("monitoring", {}).get("forbidden_tasks", [])
        for task in forbidden:
            try:
                check_result = subprocess.run(
                    f'schtasks /Query /TN "{task}" /FO LIST',
                    shell=True, capture_output=True, text=True, encoding='latin1'
                )

                if check_result.returncode != 0:
                    # Task does not exist — nothing to do
                    continue

                self.logger.warning(f"⚠️  Forbidden task '{task}' found! DELETING...")
                delete_result = subprocess.run(
                    f'schtasks /delete /tn "{task}" /f',
                    shell=True, capture_output=True, text=True, encoding='latin1'
                )

                if delete_result.returncode == 0:
                    self.logger.info(f"✅ Forbidden task '{task}' successfully DELETED.")
                    self.log_event("TASK_DELETED", f"Scheduled task '{task}' was deleted.")
                else:
                    err = delete_result.stderr.strip() or delete_result.stdout.strip()
                    self.logger.error(f"❌ Failed to delete task '{task}'. Error: {err}")

            except Exception as e:
                self.logger.error(f"Exception while managing task '{task}': {e}")

    # ------------------------------------------------------------------
    # Main monitoring cycle
    # ------------------------------------------------------------------

    def run_cycle(self):
        """Runs a single monitoring cycle."""
        self.logger.info("--- Monitoring Cycle START ---")
        reboot_settings = self.settings.get("reboot_prevention", {})

        # 1. App Health check
        self.ensure_apps_running()
        self.ensure_butt_connected()
        process_status = self.check_processes()
        self.logger.info(f"Process Status: {process_status}")

        # 2. Activity Check — skip if suspended or in a live session
        if self.suspended:
            self.logger.info("[SUSPENSO] Verificação de atividade ignorada por suspensão manual.")
        elif self.live_session_active:
            self.logger.info("Skipping playback activity check (LIVE SESSION ACTIVE).")
        else:
            is_active = self.check_playback_activity()
            if not is_active and process_status.get("zararadio") == "Running":
                self.logger.warning("ZaraRadio possibly stuck. Attempting to trigger PLAY...")
                self.trigger_play_on_zara()

        # 3. Log Analysis
        zararadio_logs = self.log_analyser.analyse_zararadio()
        if zararadio_logs:
            self.logger.info(f"Latest ZaraRadio log entry: {zararadio_logs[-1]}")

        # 4. Volume Control (Limit to 24%)
        self.audio_manager.limit_app_volume("ZaraRadio.exe")

        # 5. Task Management (Disable forbidden reboots)
        self.manage_tasks()

        # 6. System Health
        health = self.check_system_health()
        free_mb = health.get("ram_kb_free", 0) // 1024
        self.logger.info(
            f"Health — CPU: {health.get('cpu_percent', 'N/A')}% | "
            f"RAM: {health.get('ram_percent', 'N/A')}% used | "
            f"Free RAM: {free_mb} MB"
        )

        # 7. Suppress Sleep / Reboot
        self.reboot_blocker.prevent_sleep()
        if reboot_settings.get("abort_shutdown_periodically"):
            self.reboot_blocker.abort_shutdown()

        self.logger.info("--- Monitoring Cycle END ---")

    # ------------------------------------------------------------------
    # Daily report
    # ------------------------------------------------------------------

    def check_and_send_daily_report(self):
        """Checks if it is report time and sends the operational report."""
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        report_time_str = (
            self.settings.get("notifications", {})
            .get("email", {})
            .get("report_time", "07:00")
        )
        try:
            report_hour, report_minute = map(int, report_time_str.split(":"))
        except ValueError:
            report_hour, report_minute = 7, 0

        if (
            now.hour == report_hour
            and now.minute == report_minute
            and self.last_report_date != current_date
        ):
            self.logger.info(
                f"Report time reached ({report_time_str}). Preparing operational summary..."
            )

            zara_running = self.check_processes().get("zararadio") == "Running"
            butt_count = sum(
                1 for p in psutil.process_iter(['name'])
                if p.info['name'].lower() == 'butt.exe'
            )
            restarts = sum(1 for e in self.daily_events if e['type'] == 'RESTART')

            summary = {
                "zara_status": "ONLINE" if zara_running else "OFFLINE",
                "butt_count": butt_count,
                "restarts": restarts,
                "events": list(self.daily_events)
            }

            # On Mondays, attach the weekly execution report
            attachment = None
            if now.weekday() == 0:  # 0 = Monday
                self.logger.info("Monday detected. Generating weekly execution CSV...")
                attachment = self.weekly_generator.generate_report(7)

            success = self.email_reporter.send_daily_report(summary, attachment_path=attachment)
            if success:
                self.last_report_date = current_date
                self.daily_events.clear()

    # ------------------------------------------------------------------
    # vMix / Live session management
    # ------------------------------------------------------------------

    def check_vmix_and_switch(self):
        """High-frequency check for vMix sessions to automate audio switching."""
        is_live, title = self.vmix.is_session_live()

        if is_live and not self.live_session_active:
            self.logger.info(f"🚨 LIVE SESSION DETECTED IN VMIX: '{title}'")
            self.logger.info("Pausing local programming and releasing NDI audio...")
            self.live_session_active = True
            self.audio_manager.limit_app_volume("ZaraRadio.exe", limit=0.0)
            self.audio_manager.limit_app_volume("NDI Monitor.exe", limit=1.0)
            self.log_event("LIVE_START", f"Live session started via vMix: {title}")

        elif not is_live and self.live_session_active:
            self.logger.info(f"🏁 END OF LIVE SESSION DETECTED IN VMIX (Current Input: {title})")
            self.logger.info("Resuming normal ZaraRadio programming...")
            self.live_session_active = False
            self.audio_manager.limit_app_volume("ZaraRadio.exe", limit=0.24)
            self.trigger_play_on_zara()
            self.audio_manager.limit_app_volume("NDI Monitor.exe", limit=0.0)
            self.log_event("LIVE_END", "Live session ended. Radio resumed.")

    def check_zara_track_and_trigger_vmix(self):
        """Checks current ZaraRadio track and triggers vMix scenes based on keywords."""
        vmix_cfg = self.settings.get("vmix", {})
        if not vmix_cfg.get("enabled", False):
            return

        current_track = self.get_zara_current_track()
        if not current_track or current_track == self.last_track:
            return

        self.last_track = current_track
        self.logger.info(f"New track detected: {current_track}")

        triggers = vmix_cfg.get("track_triggers", {})
        upper_track = current_track.upper()

        for kw, action in triggers.items():
            if kw.upper() in upper_track:
                self.logger.info(f"🎯 Trigger Match: '{kw}' found in '{current_track}'")
                self.vmix.send_command(
                    function=action.get("function", "Cut"),
                    input_name=action.get("input")
                )
                break

    def check_ndi_session(self):
        """Detects if an NDI Monitor session or Plenário window is active to prevent ZaraRadio interference."""
        ndi_active = False
        def callback(hwnd, extra):
            nonlocal ndi_active
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).lower()
                # Padrões para detectar transmissão do plenário via NDI Monitor
                if "ndi monitor" in title or "plenário" in title or "plenario" in title or "sessão" in title or "sessao" in title:
                    ndi_active = True
        
        try:
            win32gui.EnumWindows(callback, None)
        except:
            pass
        
        if ndi_active and not self.suspended:
            self.logger.info("📡 NDI MONITOR / PLENÁRIO DETECTADO. Suspendendo automação do ZaraRadio.")
            self.suspended = True
        elif not ndi_active and self.suspended:
            # Só retomamos se não houver suspensão manual por outro motivo
            self.logger.info("🏁 NDI Monitor / Plenário encerrado. Retomando automação.")
            self.suspended = False

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        """Main loop of the monitoring agent."""
        interval = self.settings.get("monitoring", {}).get("interval_seconds", 60)

        self.reboot_blocker.prevent_sleep()
        self.reboot_blocker.apply_registry_blocks()

        self.logger.info(f"Monitoring loop started. System cycle interval: {interval}s")
        
        last_cycle_time = 0

        while True:
            try:
                now = time.time()
                
                # 1. System Cycle (Health, health check, logs)
                if now - last_cycle_time >= interval:
                    if not self.live_session_active:
                        self.run_cycle()
                    self.check_and_send_daily_report()
                    last_cycle_time = now
                
                # 2. High-Frequency Checks (vMix sessions, NDI Monitor and ZaraRadio tracks)
                self.check_vmix_and_switch()
                self.check_ndi_session() # Nova checagem do NDI
                self.check_zara_track_and_trigger_vmix()
                
            except Exception as e:
                # Top-level guard: log but never crash the monitoring loop
                self.logger.critical(f"Unhandled exception in monitoring loop: {e}", exc_info=True)

            time.sleep(1)  # High-frequency check every second


if __name__ == "__main__":
    monitor = RadioMonitor()
    monitor.run()


