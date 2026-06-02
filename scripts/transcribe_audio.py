import os
import subprocess
import tempfile
import whisper

# Injeta o caminho do ffmpeg no PATH do sistema para o Whisper localiza-lo
ffmpeg_dir = r"C:\ProgramData\chocolatey\bin"
if ffmpeg_dir not in os.environ["PATH"]:
    os.environ["PATH"] += os.pathsep + ffmpeg_dir

def transcribe_audio_slice(audio_path, limit_seconds=90):
    """
    Corta os primeiros segundos de um audio e realiza a transcricao via Whisper.
    
    :param audio_path: Caminho completo para o arquivo de audio de entrada (.mp3).
    :param limit_seconds: Duracao do corte em segundos (padrao 90s).
    :return: String com o texto transcrito ou None se falhar.
    """
    if not os.path.exists(audio_path):
        print(f"Erro: Arquivo nao encontrado em {audio_path}")
        return None
        
    temp_fd, temp_path = tempfile.mkstemp(suffix=".mp3")
    os.close(temp_fd) # Fecha o descritor para que o ffmpeg possa escrever
    
    try:
        # Comando ffmpeg para cortar os primeiros N segundos de audio
        ffmpeg_cmd = [
            r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
            "-y",
            "-i", audio_path,
            "-ss", "0",
            "-t", str(limit_seconds),
            "-acodec", "libmp3lame",
            temp_path
        ]
        
        # Executa o corte silenciosamente
        subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        # Verifica se o arquivo temporario foi gerado e possui tamanho
        if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
            print("Erro: Falha ao gerar o corte de audio com FFmpeg.")
            return None
            
        # Carrega o modelo Tiny do Whisper (adequado para execucao rapida em CPU)
        model = whisper.load_model("tiny")
        
        # Transcreve o corte de audio
        # fp16=False eh obrigatorio/recomendado para rodar em CPU sem avisos
        result = model.transcribe(temp_path, fp16=False, language="pt")
        
        return result.get("text", "").strip()
        
    except Exception as e:
        print(f"Erro durante a transcricao do audio: {e}")
        return None
    finally:
        # Garante a limpeza do arquivo temporario
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                print(f"Aviso ao remover arquivo temporario: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"Transcrevendo os primeiros 90s de: {file_path}")
        texto = transcribe_audio_slice(file_path)
        if texto:
            print("\nTranscricao obtida com sucesso:\n")
            print(texto)
        else:
            print("\nFalha na transcricao.")
    else:
        print("Uso: python transcribe_audio.py <caminho_do_audio>")
