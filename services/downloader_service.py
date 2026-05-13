import os
import re
import logging
import subprocess
from pathlib import Path
import yt_dlp

logger = logging.getLogger("OmniCore.DownloaderService")

class DownloaderService:
    def __init__(self, target_dir: str = r"D:\RADIO\QUARENTENA_TJ"):
        self.target_dir = Path(target_dir)
        self.target_dir.mkdir(exist_ok=True, parents=True)
        # Caminho detectado do FFmpeg para garantir funcionamento do yt-dlp
        self.ffmpeg_path = r"C:\Users\STREAMING\OneDrive\ARQUIVOS STREAMING\PROGRAMA_MUSICAS"
        self.active_progress = {} # {query: {percentage: 0, status: 'idle', total_bytes: 0, downloaded_bytes: 0}}

    def _progress_hook(self, d, query):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%').replace('%', '').strip()
            try:
                self.active_progress[query] = {
                    "percentage": float(p),
                    "status": "downloading",
                    "speed": d.get('_speed_str', '0KB/s'),
                    "eta": d.get('_eta_str', '00:00')
                }
            except: pass
        elif d['status'] == 'finished':
            self.active_progress[query] = {
                "percentage": 100,
                "status": "processing", # FFmpeg post-processing
                "speed": "0KB/s",
                "eta": "00:00"
            }

    def search_and_download(self, query: str, destination: str = None) -> dict:
        """
        Busca no YouTube pelo termo e faz o download.
        Aplica filtro de silêncio e normalização básica.
        """
        dest_path = Path(destination) if destination else self.target_dir
        dest_path.mkdir(exist_ok=True, parents=True)

        self.active_progress[query] = {"percentage": 0, "status": "searching", "speed": "0KB/s", "eta": "00:00"}

        # Adiciona o diretório do FFmpeg ao PATH do processo atual
        if self.ffmpeg_path not in os.environ["PATH"]:
            os.environ["PATH"] += os.pathsep + self.ffmpeg_path

        # Limpa o nome do arquivo para o Windows
        filename_base = re.sub(r'[\\/*?:"<>|]', "", query).strip()
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'ffmpeg_location': os.path.join(self.ffmpeg_path, "ffmpeg.exe"),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            # Filtro de silêncio: corta início e fim
            'postprocessor_args': ['-af', 'silenceremove=1:0:-50dB'],
            'outtmpl': str(dest_path / f'{filename_base}.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch1:', # Pega o primeiro resultado
            'progress_hooks': [lambda d: self._progress_hook(d, query)],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=True)
                # Se for busca, o info['entries'] terá os dados
                if 'entries' in info:
                    video_info = info['entries'][0]
                else:
                    video_info = info
                
                actual_filename = dest_path / f"{filename_base}.mp3"
                
                # Limpeza preventiva de possíveis sobras de .webm ou .part
                for ext in [".webm", ".part", ".ytdl"]:
                    temp_f = dest_path / f"{filename_base}{ext}"
                    if temp_f.exists():
                        try: os.remove(temp_f)
                        except: pass

                self.active_progress[query] = {"percentage": 100, "status": "completed", "speed": "0KB/s", "eta": "00:00"}
                logger.info(f"[Downloader] Sucesso: {query} -> {actual_filename}")
                return {
                    "success": True, 
                    "path": str(actual_filename), 
                    "title": video_info.get('title'),
                    "duration": video_info.get('duration')
                }
        except Exception as e:
            self.active_progress[query] = {"percentage": 0, "status": "failed", "error": str(e)}
            logger.error(f"[Downloader] Erro ao baixar {query}: {e}")
            return {"success": False, "error": str(e)}
        finally:
            # Mantém por um tempo para o frontend ler e depois remove
            # Ou o chamador remove. Vamos deixar por enquanto.
            pass

    def trim_silence_manually(self, file_path: str):
        """
        Caso o postprocessor do yt-dlp falhe ou queiramos rodar depois.
        Usa ffmpeg diretamente.
        """
        temp_output = file_path.replace(".mp3", "_trimmed.mp3")
        cmd = [
            'ffmpeg', '-y', '-i', file_path, 
            '-af', 'silenceremove=1:0:-50dB', 
            temp_output
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            os.replace(temp_output, file_path)
            return True
        except Exception as e:
            logger.error(f"[Downloader] Erro ao trimar silêncio: {e}")
            return False

downloader_instance = DownloaderService()
