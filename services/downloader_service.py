import os
import re
import logging
import asyncio
import threading
from pathlib import Path
import yt_dlp

logger = logging.getLogger("OmniCore.DownloaderService")

class DownloaderService:
    """
    Serviço robusto de download de áudio via yt-dlp.
    Suporta busca, extração de metadados, normalização e progresso em tempo real.
    """
    def __init__(self, target_dir: str = r"D:\RADIO\QUARENTENA_TJ"):
        self.target_dir = Path(target_dir)
        self.target_dir.mkdir(exist_ok=True, parents=True)
        # FFmpeg é essencial para extração de MP3 e filtros
        self.ffmpeg_path = r"C:\Users\STREAMING\OneDrive\ARQUIVOS STREAMING\PROGRAMA_MUSICAS"
        self.active_progress = {} # {id: {percentage: 0, status: 'idle', title: ''}}
        self._lock = threading.Lock()

    def _progress_hook(self, d, task_id):
        with self._lock:
            if d['status'] == 'downloading':
                p = d.get('_percent_str', '0%').replace('%', '').strip()
                try:
                    self.active_progress[task_id].update({
                        "percentage": float(p),
                        "status": "downloading",
                        "speed": d.get('_speed_str', '0KB/s'),
                        "eta": d.get('_eta_str', '00:00')
                    })
                except: pass
            elif d['status'] == 'finished':
                self.active_progress[task_id].update({
                    "percentage": 100,
                    "status": "processing"
                })

    def clean_filename(self, text: str) -> str:
        """Remove caracteres proibidos no Windows e excesso de espaços."""
        # Remove coisas comuns em títulos de YouTube que não queremos no arquivo
        text = re.sub(r'\(Official (Video|Audio|Lyric|Music Video)\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[Official (Video|Audio|Lyric|Music Video)\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\(Clip\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'[\\/*?:"<>|]', "", text)
        return " ".join(text.split()).strip()

    def search_and_download(self, query: str, destination: str = None) -> dict:
        """
        Executa a busca e o download de forma síncrona (geralmente chamado por um Worker).
        """
        task_id = re.sub(r'\W+', '', query)[:20] + "_" + str(os.getpid())
        dest_path = Path(destination) if destination else self.target_dir
        dest_path.mkdir(exist_ok=True, parents=True)

        with self._lock:
            self.active_progress[task_id] = {
                "query": query,
                "percentage": 0,
                "status": "searching",
                "title": "Buscando...",
                "id": task_id
            }

        # Garante que FFmpeg esteja acessível
        if self.ffmpeg_path not in os.environ["PATH"]:
            os.environ["PATH"] += os.pathsep + self.ffmpeg_path

        ydl_opts = {
            'format': 'bestaudio/best',
            'ffmpeg_location': os.path.join(self.ffmpeg_path, "ffmpeg.exe"),
            'noplaylist': True,
            'default_search': 'ytsearch1:',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            # silenceremove=1:0:-50dB remove silêncio do início
            # silenceremove=stop_periods=-1:stop_duration=1:stop_threshold=-50dB remove do fim
            'postprocessor_args': ['-af', 'silenceremove=start_periods=1:start_silence=0:start_threshold=-50dB,loudnorm'],
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [lambda d: self._progress_hook(d, task_id)],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Primeiro apenas extrai info para decidir o nome do arquivo final
                info = ydl.extract_info(query, download=False)
                if 'entries' in info:
                    video_info = info['entries'][0]
                else:
                    video_info = info

                yt_title = video_info.get('title', 'Unknown Title')
                filename_base = self.clean_filename(yt_title)
                
                # Se a query original for "Artista - Musica", preferimos manter a estrutura se possível
                if " - " in query and len(query) < 100:
                    filename_base = self.clean_filename(query)

                final_filename = f"{filename_base}.mp3"
                actual_path = dest_path / final_filename
                
                with self._lock:
                    self.active_progress[task_id]["title"] = yt_title

                # Agora baixa com o nome correto
                ydl_opts['outtmpl'] = str(dest_path / f'{filename_base}.%(ext)s')
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_real:
                    ydl_real.download([query])

                logger.info(f"[Downloader] Completo: {yt_title} -> {actual_path}")
                
                with self._lock:
                    self.active_progress[task_id]["status"] = "completed"
                    self.active_progress[task_id]["percentage"] = 100

                return {
                    "success": True,
                    "path": str(actual_path),
                    "title": yt_title,
                    "duration": video_info.get('duration'),
                    "id": video_info.get('id')
                }

        except Exception as e:
            logger.error(f"[Downloader] Falha crítica ao baixar '{query}': {e}")
            with self._lock:
                self.active_progress[task_id].update({
                    "status": "failed",
                    "error": str(e)
                })
            return {"success": False, "error": str(e)}
        finally:
            # Mantém no cache por 30 segundos para a UI ler
            threading.Timer(30, self._cleanup_progress, args=[task_id]).start()

    def _cleanup_progress(self, task_id):
        with self._lock:
            if task_id in self.active_progress:
                del self.active_progress[task_id]

downloader_instance = DownloaderService()
