import threading
import logging
import pystray
from PIL import Image, ImageDraw
import os

logger = logging.getLogger("OmniCore.GUI.Tray")

def create_tray_image():
    img = Image.new('RGB', (64, 64), color='black')
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, 56, 56), fill='#0ea5e9')
    return img

def on_force_play(icon, item):
    from services.guardian_service import guardian_instance
    guardian_instance.log_event("TRAY", "Comando manual: Forçar Play (P).")
    guardian_instance.force_play()

def on_restart_studio(icon, item):
    from services.guardian_service import guardian_instance
    guardian_instance.log_event("TRAY", "Comando manual: Reiniciar Estúdio.")
    threading.Thread(target=guardian_instance.restart_zara, daemon=True).start()
    # Adicionar lógica de reiniciar BUTT se necessário

def on_sync_acervo(icon, item):
    from services.guardian_service import guardian_instance
    guardian_instance.log_event("TRAY", "Comando manual: Sincronizar Acervo.")
    # Chamada direta via thread para não travar a UI
    from core.database import SessionLocal
    from routers.acervo import sincronizar_acervo
    db = SessionLocal()
    threading.Thread(target=lambda: sincronizar_acervo(db), daemon=True).start()

def on_generate_now(icon, item):
    from services.guardian_service import guardian_instance
    guardian_instance.log_event("TRAY", "Comando manual: Gerar Programação 24h.")
    from director.playlist_engine import playlist_engine_instance
    threading.Thread(target=playlist_engine_instance.gerar_programacao_diaria, daemon=True).start()

def on_reload_config(icon, item):
    from services.guardian_service import guardian_instance
    guardian_instance.log_event("TRAY", "Comando manual: Recarregar Configurações.")
    from director import grade_rules as GR
    cfg = GR.recarregar_config()
    logging.info(f"Configurações recarregadas via Tray: {cfg}")

def on_open_dashboard(icon, item):
    import webbrowser
    webbrowser.open("http://localhost:8001")

def on_exit(icon, item):
    from worker_manager import worker_manager_instance
    logger.info("Encerrando Omni Core via ícone de bandeja...")
    worker_manager_instance.stop_orchestrator()
    icon.stop()
    os._exit(0)

def start_tray_icon(root):
    try:
        image = create_tray_image()
        menu = pystray.Menu(
            pystray.MenuItem("Exibir Monitor", lambda i, n: root.after(0, root.deiconify)),
            pystray.MenuItem("🎵 Gerar Programação (Agora)", on_generate_now),
            pystray.MenuItem("📦 Sincronizar Acervo", on_sync_acervo),
            pystray.MenuItem("⚙️ Recarregar Configurações", on_reload_config),
            pystray.MenuItem("🌐 Abrir Dashboard Web", on_open_dashboard),
            pystray.MenuItem("❌ Sair do Omni Core", on_exit)
        )
        icon = pystray.Icon("omni_core", image, "Omni Core V2", menu)
        icon.run()
    except Exception as e:
        logger.error(f"Falha ao iniciar ícone de bandeja: {e}")