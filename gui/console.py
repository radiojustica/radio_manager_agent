import tkinter as tk
from tkinter import ttk, scrolledtext
import time
import logging
import webbrowser

logger = logging.getLogger("OmniCore.GUI.Console")

class RadioAgentGUI:
    def __init__(self, root, guardian):
        self.root = root
        self.guardian = guardian
        self.root.title("Omni Core - Console Master")
        self.root.geometry("950x700")
        self.root.configure(bg="#0f172a")

        # Tray synchronization
        self.root.protocol("WM_DELETE_WINDOW", lambda: self.root.withdraw())

        self.setup_ui()
        self.update_status_loop()

    def setup_ui(self):
        # Frame de Cabeçalho
        header = tk.Frame(self.root, bg="#1e293b", height=60)
        header.pack(fill="x")
        tk.Label(header, text="CONEXÃO OMNI CORE V2", font=("Outfit", 14, "bold"), fg="#22d3ee", bg="#1e293b", padx=20).pack(side="left")

        # Frame principal
        main_frame = tk.Frame(self.root, bg="#0f172a")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Área de log
        self.log_area = scrolledtext.ScrolledText(
            main_frame,
            bg="#020617",
            fg="#cbd5e1",
            font=("Consolas", 10),
            padx=10, pady=10,
            borderwidth=0
        )
        self.log_area.pack(fill="both", expand=True)

        self.setup_logs()

        # Barra de status
        self.status_var = tk.StringVar(value="Sincronizando Motores...")
        status_frame = tk.Frame(main_frame, bg="#0f172a", pady=10)
        status_frame.pack(fill="x")
        
        tk.Label(status_frame, textvariable=self.status_var, bg="#0f172a", fg="#94a3b8", font=("Inter", 9, "bold")).pack(side="left")
        
        tk.Button(
            status_frame, 
            text="ABRIR DASHBOARD WEB", 
            command=self.on_open_dashboard,
            bg="#22d3ee", fg="#0f172a", 
            font=("Inter", 8, "bold"),
            padx=10
        ).pack(side="right")

    def on_open_dashboard(self):
        try:
            webbrowser.open("http://localhost:8001")
        except Exception as e:
            self.log(f"Falha ao abrir dashboard: {e}", tag="error")

    def setup_logs(self):
        """Configura as tags de formatação para a área de log."""
        self.log_area.tag_config("time", foreground="#94a3b8")
        self.log_area.tag_config("info", foreground="#22d3ee")
        self.log_area.tag_config("warning", foreground="#fbbf24")
        self.log_area.tag_config("error", foreground="#f43f5e")
        self.log_area.tag_config("success", foreground="#10b981")

    def log(self, message, tag="info"):
        """Adiciona uma mensagem formatada à área de log."""
        timestamp = time.strftime("%H:%M:%S")
        try:
            self.log_area.insert(tk.END, f"[{timestamp}] ", "time")
            self.log_area.insert(tk.END, f"{message}\n", tag)
            self.log_area.see(tk.END)
        except: pass

    def update_status_loop(self):
        try:
            zara_on = "ON" if self.guardian.check_processes().get("zararadio") == "Running" else "OFF"
            self.status_var.set(f"ZARA: {zara_on} | TELEMETRIA: ATIVA | DASHBOARD: http://localhost:8001")
        except: pass
        self.root.after(5000, self.update_status_loop)

    def on_open_dashboard(self):
        import webbrowser
        webbrowser.open("http://localhost:8001")