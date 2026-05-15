import os
import re
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from uuid import uuid4
import yt_dlp

logger = logging.getLogger("OmniCore.YoutubeDLManager")


class YoutubeDLManager:
    """
    Gerenciador centralizado para operações com yt-dlp.
    Abstrai configurações, retry e progress tracking.
    """

    def __init__(
        self,
        ffmpeg_path: str = r"C:\Users\STREAMING\OneDrive\ARQUIVOS STREAMING\PROGRAMA_MUSICAS",
        max_retries: int = 3,
        timeout_seconds: int = 300,
    ):
        self.ffmpeg_path = ffmpeg_path
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self._ensure_ffmpeg_in_path()

    def _ensure_ffmpeg_in_path(self):
        """Garante que FFmpeg esteja acessível no PATH."""
        if self.ffmpeg_path not in os.environ.get("PATH", ""):
            os.environ["PATH"] += os.pathsep + self.ffmpeg_path
            logger.debug(f"FFmpeg adicionado ao PATH: {self.ffmpeg_path}")

    def get_base_options(self) -> Dict[str, Any]:
        """Retorna opcões base para yt-dlp (reutilizável)."""
        return {
            "format": "bestaudio/best",
            "ffmpeg_location": os.path.join(self.ffmpeg_path, "ffmpeg.exe"),
            "noplaylist": True,
            "default_search": "ytsearch1:",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "postprocessor_args": [
                "-af",
                "silenceremove=start_periods=1:start_silence=0:start_threshold=-50dB,loudnorm",
            ],
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": self.timeout_seconds,
        }

    def extract_info(
        self,
        query: str,
        progress_hook: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Extrai informações de um vídeo sem baixar.
        Útil para obter metadados antes de fazer download.
        """
        opts = self.get_base_options()
        if progress_hook:
            opts["progress_hooks"] = [progress_hook]

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(query, download=False)
                if "entries" in info:
                    return info["entries"][0] if info["entries"] else {}
                return info
        except Exception as e:
            logger.error(f"Erro ao extrair info de '{query}': {e}")
            raise

    def download(
        self,
        query: str,
        output_path: Path,
        filename_template: str = "%(title)s.%(ext)s",
        progress_hook: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Baixa áudio de uma query com retry automático e timeout.

        Returns:
            Dict com resultado do download ou exceção
        """
        attempt = 0
        last_error = None

        while attempt < self.max_retries:
            attempt += 1
            try:
                opts = self.get_base_options()
                opts["outtmpl"] = str(output_path / filename_template)

                if progress_hook:
                    opts["progress_hooks"] = [progress_hook]

                logger.debug(
                    f"Tentativa {attempt}/{self.max_retries} para '{query}'"
                )
                with yt_dlp.YoutubeDL(opts) as ydl:
                    result = ydl.download([query])

                if result == 0:
                    return {"success": True, "attempt": attempt}
                else:
                    last_error = f"yt-dlp retornou código {result}"

            except yt_dlp.utils.DownloadError as e:
                last_error = f"Download error: {str(e)}"
                if attempt < self.max_retries:
                    logger.warning(
                        f"Retry {attempt}/{self.max_retries} após erro: {last_error}"
                    )
            except Exception as e:
                last_error = f"Erro inesperado: {str(e)}"
                logger.warning(
                    f"Retry {attempt}/{self.max_retries} após erro: {last_error}"
                )

        logger.error(f"Download falhou após {self.max_retries} tentativas: {last_error}")
        return {"success": False, "error": last_error, "attempts": self.max_retries}

    @staticmethod
    def clean_filename(text: str) -> str:
        """Remove caracteres proibidos e metadados indesejados."""
        text = re.sub(
            r"\(Official (Video|Audio|Lyric|Music Video)\)",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\[Official (Video|Audio|Lyric|Music Video)\]",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"\(Clip\)", "", text, flags=re.IGNORECASE)
        text = re.sub(r'[\\/*?:"<>|]', "", text)
        return " ".join(text.split()).strip()

    @staticmethod
    def generate_task_id(query: str) -> str:
        """Gera um ID único para rastreamento de download."""
        return str(uuid4())
