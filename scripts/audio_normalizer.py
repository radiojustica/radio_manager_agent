import os
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("OmniCore.AudioNormalizer")

def normalize_audio(input_path: str, output_path: str, target_lufs: float = -14.0):
    """
    Normaliza o volume do áudio usando o padrão EBU R128 via filtro loudnorm do ffmpeg.
    """
    if not os.path.exists(input_path):
        logger.error(f"Arquivo de entrada não encontrado: {input_path}")
        return False

    # Garante que o diretório de saída exista
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Comando FFmpeg para loudnorm (One-pass)
    # I = Integrated loudness target
    # LRA = Loudness range target
    # TP = True peak target
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-af', f'loudnorm=I={target_lufs}:LRA=11:TP=-1.5',
        '-c:a', 'libmp3lame', '-b:a', '192k',
        output_path
    ]

    try:
        logger.info(f"Normalizando: {os.path.basename(input_path)} para {target_lufs} LUFS")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro no FFmpeg ao normalizar {input_path}: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Erro inesperado na normalização: {e}")
        return False

def process_folder(folder_path: str, output_folder: str):
    """Processa todos os arquivos de áudio em uma pasta."""
    supported = ('.mp3', '.wav', '.m4a', '.ogg')
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(supported)]
    
    success_count = 0
    for file in files:
        in_p = os.path.join(folder_path, file)
        out_p = os.path.join(output_folder, file)
        if normalize_audio(in_p, out_p):
            success_count += 1
            
    return success_count
