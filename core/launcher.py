import logging
import sys
import threading
import time

from core import state
from core.system import is_admin, verificar_instancia_unica, run_as_admin, abrir_no_navegador
from api.manager import run_api_server, wait_for_server
from services.guardian_service import guardian_instance
from worker_manager import worker_manager_instance

logger = logging.getLogger("OmniCore.Launcher")


def run_app() -> None:
    """Inicia o sistema com a interface gráfica (GUI)."""
    try:
        import tkinter as tk
        from gui.console import RadioAgentGUI
        from gui.tray import start_tray_icon
    except ImportError as e:
        logger.warning(f"Dependências de UI não encontradas ({e}). Iniciando em modo Headless...")
        from director.orchestrator import system_orchestrator
        system_orchestrator.bootstrap(open_browser_if_running=True)
        system_orchestrator.start_core()
        system_orchestrator.run_headless()
        return

    from director.orchestrator import system_orchestrator
    
    # 1. Inicializa o Core (Admin, Mutex, API, Workers)
    system_orchestrator.bootstrap(open_browser_if_running=True)
    system_orchestrator.start_core()

    # 2. Cria interface Tkinter
    logger.info("Configurando interface gráfica (Tkinter)...")
    try:
        root = tk.Tk()
        # Retiramos a janela da tela IMEDIATAMENTE
        root.withdraw()
        state.SHOW_UI_CALLBACK = lambda: root.after(0, root.deiconify)
    except Exception as e:
        logger.error(f"Erro ao criar interface Tkinter: {e}")
        # Se falhar a UI, o core já está rodando. Podemos decidir se morre ou continua.
        # Por segurança, vamos manter o core rodando headless se a UI falhar.
        system_orchestrator.run_headless()
        return

    # 3. Inicia ícone de bandeja em thread
    logger.info("Iniciando ícone de bandeja...")
    threading.Thread(target=lambda: start_tray_icon(root), daemon=True).start()

    # 4. GUI principal
    logger.info("Configurando console GUI...")
    gui = RadioAgentGUI(root, guardian_instance)

    # 5. Bridge de logging para a GUI
    class GuiLogBridge(logging.Handler):
        def emit(self, record):
            tag = "info"
            if record.levelno >= logging.ERROR:
                tag = "error"
            elif record.levelno >= logging.WARNING:
                tag = "warning"
            try:
                root.after(0, lambda: gui.log(record.getMessage(), tag))
            except Exception:
                pass

    if hasattr(guardian_instance, 'logger'):
        guardian_instance.logger.addHandler(GuiLogBridge())

    # 6. Autostart Dashboard
    def open_browser():
        if wait_for_server():
            abrir_no_navegador("http://127.0.0.1:8001")

    threading.Thread(target=open_browser, daemon=True).start()

    logger.info("Sistema pronto (GUI). Dashboard em http://127.0.0.1:8001")
    root.mainloop()

if __name__ == "__main__":
    run_app()
