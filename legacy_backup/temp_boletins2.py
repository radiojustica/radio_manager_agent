import os
import sys
import re
import time
import io
import json
import asyncio
import urllib.request
import pandas as pd
import openpyxl
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.voice_queue import VoiceQueue
from core.best_practices import retry_async, aplicar_pronuncia, carregar_env_var
from datetime import datetime
from pydub import AudioSegment
import glob

workspace_dir = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
sys.path.append(workspace_dir)
project_root = os.path.dirname(os.path.dirname(workspace_dir))
sys.path.append(project_root)
jornal_dir = os.path.join(os.path.dirname(workspace_dir), "jornal").replace("\\", "/")
sys.path.append(jornal_dir)

try:
    from processar_roteiro_completo import limpar_texto_locutor
except ImportError:
    print("[AVISO] Não foi possível importar 'limpar_texto_locutor'. Usando fallback.")
    def limpar_texto_locutor(texto):
        return texto

SPREADSHEET_ID = "1b1xnzvA00H1JC9uTvd6c-PBwQjEzGRs6t_raXG_ztsU"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=xlsx"
DRIVE_DIR = carregar_env_var("DRIVE_BOLETINS_DIR", r"H:/Meu Drive/RADIO TJRN CONTEÚDO/00_PRODUCAO_2026/07_MODELOS_TUTORIAIS")
LOCAL_BOLETINS_DIR = os.path.join(workspace_dir, "boletins").replace("\\", "/")

ROTEIROS_DIR_BOLETINS = r"H:\Meu Drive\RADIO TJRN CONTEÚDO\00_PRODUCAO_2026\01_BOLETINS_DIARIOS\01_ROTEIROS"

def obter_webapp_url():
    try:
        project_root = os.path.dirname(os.path.dirname(workspace_dir))
        env_path = os.path.join(project_root, ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.split("=", 1)
                        if k.strip() == "BOLETINS_WEBAPP_URL":
                            return v.strip()
    except Exception as e:
        print(f"[AVISO] Falha ao carregar URL do Web App: {e}")
    return None

def enviar_atualizacoes_web_app(url, updates):
    import urllib.error
    payload = {"action": "update_status", "updates": updates}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response:
            res_content = response.read().decode('utf-8')
            res_json = json.loads(res_content)
            if res_json.get('status') == 'success':
                print(f"[OK] Planilha na nuvem atualizada com sucesso: {res_json.get('message')}")
    except Exception as e:
        print(f"[ERRO] Falha ao conectar com o Apps Script Web App: {e}")

def carregar_audio_asset(caminho, label):
    if os.path.exists(caminho):
        try:
            return AudioSegment.from_mp3(caminho)
        except Exception:
            pass
    return None

def obter_config_voz():
    voice = VoiceQueue().next_voice()
    # Mapeamento do Edge TTS para o código legacy do locutor que será salvo na planilha
    reverse_map = {
        "pt-BR-FranciscaNeural": "LIV",
        "pt-BR-AntonioNeural": "LEO",
        "pt-BR-ThalitaNeural": "LET",
        "pt-BR-ElzaNeural": "THI"
    }
    label = reverse_map.get(voice, voice.split("-")[-1].upper().replace("NEURAL", ""))
    return voice, label

def ler_e_parsear_roteiro_local(txt_path):
    if txt_path.endswith('.gdoc'):
        from core.gdoc_exporter import export_gdoc_to_txt
        from pathlib import Path
        content = export_gdoc_to_txt(Path(txt_path))
    else:
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
    lines = content.split('\n')
    cabeca_lines = []
    off_lines = []
    
    in_cabeca = False
    in_off = False
    
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            continue
            
        if re.match(r'^(?:cabeça|cabeca|cab)\b', line_strip, re.IGNORECASE):
            in_cabeca = True
            in_off = False
            parts = re.split(r'^(?:cabeça|cabeca|cab)\s*:?\s*', line_strip, flags=re.IGNORECASE)
            if len(parts) > 1 and parts[1].strip():
                cabeca_lines.append(parts[1].strip())
            continue
            
        if re.match(r'^off\b', line_strip, re.IGNORECASE):
            in_off = True
            in_cabeca = False
            parts = re.split(r'^off\s*:?\s*', line_strip, flags=re.IGNORECASE)
            if len(parts) > 1 and parts[1].strip():
                off_lines.append(parts[1].strip())
            continue
            
        if in_cabeca:
            cabeca_lines.append(line_strip)
        elif in_off:
            off_lines.append(line_strip)
            
    cabeca_text = " ".join(cabeca_lines).strip()
    off_text = " ".join(off_lines).strip()
    
    if not cabeca_text and not off_text:
        off_text = " ".join([l.strip() for l in lines if l.strip()]).strip()
        
    return cabeca_text, off_text

@retry_async(retries=3, backoff=1.0)
async def gerar_tts_com_retry(text, voice, rate="+0%"):
    import edge_tts
    text_fonetizado = aplicar_pronuncia(text)
    communicate = edge_tts.Communicate(text_fonetizado, voice, rate=rate)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    if not audio_data:
        raise Exception("Nenhum dado de áudio retornado pelo Edge TTS.")
    return audio_data

def mixar_mailing_com_bg(mailing_audio, bg_audio):
    bg_low = bg_audio - 14
    dur_mailing = len(mailing_audio)
    dur_bg = len(bg_low)
    
    if dur_bg < dur_mailing:
        repeats = (dur_mailing // dur_bg) + 1
        bg_low = bg_low * repeats
        
    bg_low = bg_low[:dur_mailing]
    bg_low = bg_low.fade_in(500).fade_out(800)
    return bg_low.overlay(mailing_audio)

async def processar_boletim_local(txt_path, assets):
    nome_arquivo = os.path.basename(txt_path)
    filename_base = os.path.splitext(nome_arquivo)[0]
    
    voice_name, speaker_name = obter_config_voz()
    print(f"\n* Processando roteiro local: {nome_arquivo}")
    
    # Gerar os caminhos das pastas correspondentes trocando 01_ROTEIROS por 02_AUDIOS_MAILING e 03_AUDIOS_RADIO
    mailing_saida_path = txt_path.replace("01_ROTEIROS", "02_AUDIOS_MAILING").replace(".txt", ".mp3").replace(".gdoc", ".mp3")
    edit_saida_path = txt_path.replace("01_ROTEIROS", "03_AUDIOS_RADIO").replace(".txt", ".mp3").replace(".gdoc", ".mp3")
    
    os.makedirs(os.path.dirname(mailing_saida_path), exist_ok=True)
    os.makedirs(os.path.dirname(edit_saida_path), exist_ok=True)
    
    try:
        cabeca_raw, off_raw = ler_e_parsear_roteiro_local(txt_path)
    except Exception as e:
        print(f"  [ERRO] Falha ao ler roteiro {txt_path}: {e}")
        return False
        
    cabeca_limpa = limpar_texto_locutor(cabeca_raw)
    off_limpa = limpar_texto_locutor(off_raw)
    
    print(f"  -> Gravando com a voz '{voice_name}' (Iniciais: {speaker_name})")
    
    try:
        cabeca_bytes = b""
        if cabeca_limpa:
            cabeca_bytes = await gerar_tts_com_retry(cabeca_limpa, voice_name, rate="+0%")
        off_bytes = b""
        if off_limpa:
            off_bytes = await gerar_tts_com_retry(off_limpa, voice_name, rate="+4%")
    except Exception as e:
        print(f"  [ERRO] Falha na síntese de voz (TTS): {e}")
        return False
        
    try:
        cabeca_seg = AudioSegment.from_mp3(io.BytesIO(cabeca_bytes)) if cabeca_bytes else AudioSegment.empty()
        off_seg = AudioSegment.from_mp3(io.BytesIO(off_bytes)) if off_bytes else AudioSegment.empty()
        
        vht_passagem = assets["vht_passagem"]
        mailing_audio = AudioSegment.empty()
        if cabeca_seg and off_seg:
            mailing_audio = cabeca_seg + vht_passagem + off_seg
        elif cabeca_seg:
            mailing_audio = cabeca_seg
        else:
            mailing_audio = off_seg
            
        mailing_audio.export(mailing_saida_path, format="mp3", bitrate="192k")
        print(f"  [OK] Mailing gerado em: {mailing_saida_path}")
        
        vht_abertura = assets["vht_abertura"]
        vht_encerramento = assets["vht_encerramento"]
        bg_boletim = assets["bg_boletim"]
        
        off_mixed = mixar_mailing_com_bg(off_seg, bg_boletim) if off_seg else AudioSegment.empty()
            
        edit_audio = vht_abertura
        if cabeca_seg and off_seg:
            edit_audio = edit_audio + cabeca_seg + vht_passagem + off_mixed
        elif cabeca_seg:
            edit_audio = edit_audio + cabeca_seg
        else:
            edit_audio = edit_audio + off_mixed
            
        edit_audio = edit_audio + vht_encerramento
        edit_audio.export(edit_saida_path, format="mp3", bitrate="192k")
        print(f"  [OK] Editada gerada em: {edit_saida_path}")
        
        # Preservar o roteiro original conforme solicitação do Tribunal de Justiça
        print(f"  [PRESERVADO] Roteiro original mantido no Drive: {txt_path}")

        return filename_base, speaker_name
    except Exception as e:
        print(f"  [ERRO] Falha no processamento ou exportação de áudio: {e}")
        return False

async def main():
    print("=== Processador Central de Boletins Rádio TJRN — Início ===")
    
    if not os.path.exists(ROTEIROS_DIR_BOLETINS):
        print(f"[INFO] Pasta de roteiros não encontrada no Drive: {ROTEIROS_DIR_BOLETINS}")
        sys.exit(0)
        
    # Busca recursiva por todos os formatos de roteiro
    todos_roteiros = []
    for ext in ["*.txt", "*.gdoc", "*.docx"]:
        todos_roteiros.extend(glob.glob(os.path.join(ROTEIROS_DIR_BOLETINS, "**", ext), recursive=True))
        
    if not todos_roteiros:
        print("\n[INFO] Nenhum arquivo de roteiro encontrado!")
        sys.exit(0)
        
    # Mapear os assets necessários
    vht_abertura_path = os.path.join(LOCAL_BOLETINS_DIR, "VHT/vht_abertura.mp3").replace("\\", "/")
    vht_encerramento_path = os.path.join(LOCAL_BOLETINS_DIR, "VHT/vht_encerramento.mp3").replace("\\", "/")
    vht_passagem_path = os.path.join(LOCAL_BOLETINS_DIR, "VHT/vht_passagem.mp3").replace("\\", "/")
    bg_boletim_path = os.path.join(LOCAL_BOLETINS_DIR, "VHT/bg_boletim.mp3").replace("\\", "/")
    
    assets = {
        "vht_abertura": carregar_audio_asset(vht_abertura_path, "Abertura"),
        "vht_encerramento": carregar_audio_asset(vht_encerramento_path, "Encerramento"),
        "vht_passagem": carregar_audio_asset(vht_passagem_path, "Passagem"),
        "bg_boletim": carregar_audio_asset(bg_boletim_path, "BG Trilha")
    }
    
    if not all(assets.values()):
        print("[ERRO CRÍTICO] Algum asset essencial faltando para o Boletim.")
        sys.exit(1)
        
    # Filtrar roteiros cuja saída de áudio de rádio já exista no Drive
    roteiros_pendentes = []
    for r in todos_roteiros:
        # Mapear para o áudio de rádio correspondente no Drive (03_AUDIOS_RADIO)
        edit_saida_path = r.replace("01_ROTEIROS", "03_AUDIOS_RADIO")
        for ext in [".txt", ".gdoc", ".docx"]:
            edit_saida_path = edit_saida_path.replace(ext, ".mp3")
            
        if os.path.exists(edit_saida_path):
            print(f"[PULADO] Áudio correspondente já existe no Drive: {os.path.basename(edit_saida_path)}")
            continue
            
        roteiros_pendentes.append(r)
        
    if not roteiros_pendentes:
        print(f"\n[INFO] Todos os {len(todos_roteiros)} roteiros já possuem áudio correspondente no Drive. Nada a fazer!")
        sys.exit(0)
        
    print(f"\n[INFO] Detectados {len(roteiros_pendentes)} novos roteiros pendentes para produção.")
    
    sem = asyncio.Semaphore(2)
    async def processar_com_sem(path):
        async with sem:
            return await processar_boletim_local(path, assets)
 
    tasks = [processar_com_sem(r) for r in roteiros_pendentes]
    results = await asyncio.gather(*tasks)
    
    sucessos = [res for res in results if res]
    print(f"\n=== PROCESSAMENTO DE BOLETINS FINALIZADO: {len(sucessos)} de {len(roteiros_pendentes)} concluídos ===")
    
if __name__ == "__main__":
    asyncio.run(main())