import os
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any
from uuid import uuid4
from services.youtube_dl_manager import YoutubeDLManager

logger = logging.getLogger("OmniCore.DownloaderService")


class DownloaderService:
    """
    Serviço robusto de download de áudio via yt-dlp.
    Suporta busca, extração de metadados, normalização e progresso em tempo real.
    """

    def __init__(
        self,
        target_dir: str = r"D:\RADIO\QUARENTENA_TJ",
        ffmpeg_path: str = r"C:\Users\STREAMING\OneDrive\ARQUIVOS STREAMING\PROGRAMA_MUSICAS",
    ):
        self.target_dir = Path(target_dir)
        self.target_dir.mkdir(exist_ok=True, parents=True)
        self.ydl_manager = YoutubeDLManager(ffmpeg_path=ffmpeg_path)
        self.active_progress: Dict[str, Dict[str, Any]] = {}  # {task_id: progress_data}
        self._lock = threading.Lock()

    def _progress_hook(self, d: Dict[str, Any], task_id: str):
        """Atualiza progresso de download com lock thread-safe."""
        with self._lock:
            if task_id not in self.active_progress:
                return

            try:
                if d["status"] == "downloading":
                    percent_str = d.get("_percent_str", "0%").replace("%", "").strip()
                    self.active_progress[task_id].update(
                        {
                            "percentage": float(percent_str) if percent_str else 0,
                            "status": "downloading",
                            "speed": d.get("_speed_str", "0KB/s"),
                            "eta": d.get("_eta_str", "00:00"),
                        }
                    )
                elif d["status"] == "finished":
                    self.active_progress[task_id].update(
                        {"percentage": 100, "status": "processing"}
                    )
            except Exception as e:
                logger.warning(f"Erro ao atualizar progress hook: {e}")

    def clean_filename(self, text: str) -> str:
        """Remove caracteres proibidos no Windows e excesso de espaços."""
        return YoutubeDLManager.clean_filename(text)

    def search_and_download(self, query: str, destination: str = None) -> Dict[str, Any]:
        """
        Executa a busca e o download de forma síncrona com retry automático.
        Usa UUID para rastreamento confiável de progresso.
        """
        task_id = self.ydl_manager.generate_task_id(query)
        dest_path = Path(destination) if destination else self.target_dir
        dest_path.mkdir(exist_ok=True, parents=True)

        with self._lock:
            self.active_progress[task_id] = {
                "query": query,
                "percentage": 0,
                "status": "searching",
                "title": "Buscando...",
                "id": task_id,
                "error": None,
            }

        try:
            logger.info(f"[Downloader] Iniciando download: {query} (ID: {task_id})")

            # Extrai informações do vídeo
            info = self.ydl_manager.extract_info(
                query,
                progress_hook=lambda d: self._progress_hook(d, task_id),
            )

            if not info:
                error_msg = "Nenhum resultado encontrado para a busca"
                logger.error(f"[Downloader] {error_msg}: {query}")
                with self._lock:
                    self.active_progress[task_id].update(
                        {"status": "failed", "error": error_msg}
                    )
                return {"success": False, "error": error_msg}

            yt_title = info.get("title", "Unknown Title")
            filename_base = self.clean_filename(yt_title)

            # Preferir estrutura "Artista - Música" da query se fornecida
            if " - " in query and len(query) < 100:
                filename_base = self.clean_filename(query)

            with self._lock:
                self.active_progress[task_id].update(
                    {"title": yt_title, "percentage": 10}
                )

            # Executa download com retry automático
            final_filename = f"{filename_base}.mp3"
            actual_path = dest_path / final_filename

            download_result = self.ydl_manager.download(
                query,
                dest_path,
                filename_template=f"{filename_base}.%(ext)s",
                progress_hook=lambda d: self._progress_hook(d, task_id),
            )

            if not download_result["success"]:
                error_msg = download_result.get("error", "Erro desconhecido no download")
                logger.error(
                    f"[Downloader] Falha após {download_result.get('attempts', 1)} tentativas: {error_msg}"
                )
                with self._lock:
                    self.active_progress[task_id].update(
                        {"status": "failed", "error": error_msg}
                    )
                return {"success": False, "error": error_msg}

            logger.info(f"[Downloader] Concluído: {yt_title} -> {actual_path}")

            with self._lock:
                self.active_progress[task_id].update(
                    {"status": "completed", "percentage": 100}
                )

            return {
                "success": True,
                "path": str(actual_path),
                "title": yt_title,
                "duration": info.get("duration"),
                "id": info.get("id"),
                "task_id": task_id,
            }

        except Exception as e:
            error_msg = f"Erro crítico: {str(e)}"
            logger.error(f"[Downloader] {error_msg} para '{query}'", exc_info=True)
            with self._lock:
                self.active_progress[task_id].update(
                    {"status": "failed", "error": error_msg}
                )
            return {"success": False, "error": error_msg}
        finally:
            # Cleanup automático após 60 segundos
            self._schedule_cleanup(task_id, delay=60)

    def _schedule_cleanup(self, task_id: str, delay: int = 60):
        """Agenda limpeza de progresso após delay em segundos."""
        timer = threading.Timer(delay, self._cleanup_progress, args=[task_id])
        timer.daemon = True
        timer.start()

    def _cleanup_progress(self, task_id: str):
        """Remove task_id do progresso ativo após consulta pela UI."""
        with self._lock:
            if task_id in self.active_progress:
                del self.active_progress[task_id]
                logger.debug(f"Progress cleanup: {task_id}")

downloader_instance = DownloaderService()
