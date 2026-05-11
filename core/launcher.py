import logging
import sys
import threading
import time
import tkinter as tk

from core import state
from core.system import is_admin, verificar_instancia_unica, run_as_admin
from api.manager import run_api_server, wait_for_server
from gui.console import RadioAgentGUI
from gui.tray import start_tray_icon
from services.guardian_service import guardian_instance
from worker_manager import worker_manager_instance

logger = logging.getLogger("OmniCore.Launcher")


def run_app() -> None:
    """Modo simplificado: sempre GUI, verifica admin, inicia tudo."""
    logger.info("Iniciando run_app...")
    if not is_admin():
        logger.info("Não é admin, solicitando elevação...")
        run_as_admin()
        sys.exit(0)

    logger.info("Verificando instância única...")
    if not verificar_instancia_unica():
        logger.warning("Instância duplicada detectada, saindo.")
        sys.exit(0)

    # 1. Inicia API em thread
    logger.info("Iniciando thread da API...")
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()

    # 2. Cria interface Tkinter
    logger.info("Criando interface Tkinter...")
    try:
        root = tk.Tk()
        state.SHOW_UI_CALLBACK = lambda: root.after(0, root.deiconify)
        root.withdraw()
        root.after(1000, root.withdraw)
    except Exception as e:
        logger.error(f"Erro ao criar Tkinter: {e}")
        return

    # 3. Inicia ícone de bandeja em thread
    logger.info("Iniciando ícone de bandeja...")
    threading.Thread(target=lambda: start_tray_icon(root), daemon=True).start()

    # 4. GUI principal
    logger.info("Configurando GUI...")
    gui = RadioAgentGUI(root, guardian_instance)

    # 5. Bridge de logging
    logger.info("Configurando bridge de logging...")
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

    # 6. Abre o navegador automaticamente quando o servidor estiver pronto
    def open_browser():
        if wait_for_server():
            import webbrowser
            logger.info("Abrindo Dashboard no navegador...")
            webbrowser.open("http://localhost:8001")

    threading.Thread(target=open_browser, daemon=True).start()

    logger.info("Sistema pronto. Dashboard em http://localhost:8001")
    root.mainloop()

if __name__ == "__main__":
    run_app()
