import os
import sys
import re
import io
import asyncio
import urllib.request
import openpyxl
from pydub import AudioSegment
import glob

current_dir = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
project_root = os.path.dirname(os.path.dirname(current_dir)).replace("\\", "/")
sys.path.append(project_root)
sys.path.append(current_dir)

from core.llm_factory import LLMFactory
try:
    from processar_roteiro_completo import limpar_texto_locutor
except ImportError:
    def limpar_texto_locutor(texto): return texto

ROTEIROS_DIR_NJUD = r"H:\Meu Drive\RADIO TJRN CONTEÚDO\00_PRODUCAO_2026\02_JORNAIS_NJUD\01_ROTEIROS"
AUDIO_MAILING_DIR_NJUD = r"H:\Meu Drive\RADIO TJRN CONTEÚDO\00_PRODUCAO_2026\02_JORNAIS_NJUD\02_AUDIOS_MAILING"

GLOBAL_VHT_DIR = os.path.join(project_root, "assets/vht").replace("\\", "/")

SYSTEM_PROMPT = """Você é um especialista em edição de roteiros de radiojornalismo. O objetivo é processar roteiros técnicos e entregá-los formatados para síntese de voz de bancada (locução alternada), mantendo TODO o conteúdo de notícias e aplicando diretrizes de rádio.

REGRAS:
1. Sem formatação Markdown.
2. NUNCA reduza ou resuma o conteúdo do roteiro. Mantenha todas as informações completas. O texto original é composto por Notas de Introdução (LOC/LOC 2) e corpos de matérias detalhadas (OFF/CONTEÚDO). Você deve integrar o texto da introdução com o respectivo corpo da matéria para cada NOTA.
3. Divida o roteiro final estritamente nas seguintes seções usando cabeçalhos entre colchetes:
   - [ESCALADA]: Contém a acolhida inicial (Olá, confira os destaques...) e a leitura de todos os destaques (manchetes).
   - [NOTA 1]: Contém a primeira notícia completa (a fusão da introdução LOC1 e do corpo da matéria OFF correspondente).
   - [NOTA 2]: Contém a segunda notícia completa (introdução + corpo).
   - [NOTA 3]: Contém a terceira notícia completa (introdução + corpo).
   - [NOTA 4]: Contém a quarta notícia completa (introdução + corpo).
   - [ENCERRAMENTO]: Contém o encerramento completo do programa (E o Notícias do Judiciário termina aqui...).
4. Dentro de cada seção, substitua as marcações originais de locutores por falas alternadas e fluidas entre:
   Speaker 1: [texto da fala]
   Speaker 2: [texto da fala]
   A Escalada deve começar obrigatoriamente com o Speaker 1. Alternar as falas a cada parágrafo ou frase para dar dinâmica de bancada.
5. NUNCA permita que os apresentadores se apresentem ou digam seus nomes ou codinomes.
6. Escrever números, valores, porcentagens, datas e horas por extenso.
7. Escrever siglas letra por letra separadas por espaço (ex: t j r n).
8. Sites de forma literal (ex: t j r n ponto jus ponto b r).
9. Linguagem simples e direta de rádio.
"""

def carregar_audio_asset(caminho, label):
    if os.path.exists(caminho):
        try:
            seg = AudioSegment.from_mp3(caminho)
            return seg
        except Exception:
            pass
    return None

def lines_to_falas(linhas):
    falas = []
    for linha in linhas:
        match = re.match(r'^(Speaker\s*[12]):\s*(?:\[.*?\])?\s*(.*)$', linha, re.IGNORECASE)
        if match:
            speaker = match.group(1).lower().replace(" ", "")
            texto = match.group(2).strip()
            if texto:
                falas.append((speaker, texto))
    return falas

def separar_secoes(texto_revisado):
    secoes = {}
    secao_atual = None
    linhas_secao = []
    
    for linha in texto_revisado.splitlines():
        linha = linha.strip()
        if not linha: continue
        
        m = re.match(r'^\[\s*(ESCALADA|NOTA\s*\d+|ENCERRAMENTO)\s*\]$', linha, re.IGNORECASE)
        if m:
            if secao_atual: secoes[secao_atual] = lines_to_falas(linhas_secao)
            secao_atual = m.group(1).upper().replace(" ", "")
            linhas_secao = []
        else:
            linhas_secao.append(linha)
            
    if secao_atual and linhas_secao:
        secoes[secao_atual] = lines_to_falas(linhas_secao)
        
    return secoes

def mix_voice_with_bg(voice_segment, bg_segment, bg_volume_db=-20):
    if len(voice_segment) == 0: return AudioSegment.empty()
    fade_in_ms = 1500
    fade_out_ms = 1500
    total_len = len(voice_segment) + fade_out_ms + 1000
    
    repeats = (total_len // len(bg_segment)) + 1
    bg_looped = (bg_segment * repeats)[:total_len]
    bg_low = bg_looped + bg_volume_db
    
    bg_low = bg_low.fade_in(fade_in_ms).fade_out(fade_out_ms)
    return bg_low.overlay(voice_segment)

async def gerar_tts_com_retry(text, voice):
    import edge_tts
    for tentativa in range(3):
        try:
            communicate = edge_tts.Communicate(text, voice)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            if audio_data: return audio_data
        except Exception as e:
            await asyncio.sleep(2 ** tentativa)
    raise Exception(f"Falha ao gerar TTS para voz {voice} apos 3 tentativas.")

async def processar_jornal_local(txt_path, assets, llm):
    nome_arquivo = os.path.basename(txt_path)
    filename_base = os.path.splitext(nome_arquivo)[0]
    
    print(f"\n* Processando roteiro de NJUD: {nome_arquivo}")
    
    audio_saida_path = txt_path.replace("01_ROTEIROS", "02_AUDIOS_MAILING").replace(".txt", ".mp3")
    os.makedirs(os.path.dirname(audio_saida_path), exist_ok=True)
    
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            roteiro_bruto = f.read()
    except Exception as e:
        print(f"  [ERRO] Falha ao ler {txt_path}: {e}")
        return False
        
    print(f"  -> Revisando roteiro via IA...")
    try:
        roteiro_revisado = llm.ask(SYSTEM_PROMPT, roteiro_bruto)
    except Exception as e:
        print(f"  [ERRO] Falha na reescrita de IA: {e}")
        return False

    secoes = separar_secoes(roteiro_revisado)
    VOZ_SPEAKER_1 = "pt-BR-FranciscaNeural"
    VOZ_SPEAKER_2 = "pt-BR-AntonioNeural"

    if secoes and ("ESCALADA" in secoes or any(k.startswith("NOTA") for k in secoes.keys())):
        print("  -> Estrutura detectada. Gravando com trilhas e vinhetas...")
        secoes_audio = {}

        for secao_nome, falas in secoes.items():
            if not falas: continue
            silence = AudioSegment.silent(duration=450)
            combined_voice = AudioSegment.empty()

            for idx, (speaker, texto) in enumerate(falas):
                voz = VOZ_SPEAKER_1 if speaker == "speaker1" else VOZ_SPEAKER_2
                texto_limpo = limpar_texto_locutor(texto)
                texto_limpo = re.sub(r'\b(?:eu\s+)?sou\s+o\s+speaker\s*[12]\b', '', texto_limpo, flags=re.IGNORECASE)
                texto_limpo = re.sub(r'\b(?:eu\s+)?sou\s+a\s+speaker\s*[12]\b', '', texto_limpo, flags=re.IGNORECASE)
                texto_limpo = re.sub(r'\bapresentador\s+virtual\b', '', texto_limpo, flags=re.IGNORECASE)
                texto_limpo = re.sub(r'\blocutor\s+virtual\b', '', texto_limpo, flags=re.IGNORECASE)
                texto_limpo = re.sub(r'\s+', ' ', texto_limpo).strip()
                texto_limpo = re.sub(r',\s*\.', '.', texto_limpo)
                if not texto_limpo: continue

                print(f"       [{secao_nome}] Sintetizando fala...")
                try:
                    seg_bytes = await gerar_tts_com_retry(texto_limpo, voz)
                    fala_seg = AudioSegment.from_mp3(io.BytesIO(seg_bytes))
                    if len(combined_voice) > 0: combined_voice += silence
                    combined_voice += fala_seg
                except Exception as e:
                    print(f"       [ERRO] Falha TTS: {e}")
                    return False

            if len(combined_voice) > 0:
                if assets.get("bg_trilha"):
                    secoes_audio[secao_nome] = mix_voice_with_bg(combined_voice, assets["bg_trilha"], bg_volume_db=-20)
                else:
                    secoes_audio[secao_nome] = combined_voice

        print("  -> Montagem final...")
        try:
            combined = AudioSegment.empty()
            if "ESCALADA" in secoes_audio:
                combined += secoes_audio["ESCALADA"]
                combined += AudioSegment.silent(duration=500)
            if assets.get("abertura"):
                combined += assets["abertura"]
                combined += AudioSegment.silent(duration=500)
            
            notas_list = ["NOTA1", "NOTA2", "NOTA3", "NOTA4"]
            added_notas = 0
            for nota_key in notas_list:
                if nota_key in secoes_audio:
                    if added_notas > 0 and assets.get("passagem"):
                        combined += assets["passagem"]
                        combined += AudioSegment.silent(duration=500)
                    combined += secoes_audio[nota_key]
                    combined += AudioSegment.silent(duration=500)
                    added_notas += 1
                    
            if "ENCERRAMENTO" in secoes_audio:
                if added_notas > 0 and assets.get("passagem"):
                    combined += assets["passagem"]
                    combined += AudioSegment.silent(duration=500)
                combined += secoes_audio["ENCERRAMENTO"]

            if assets.get("encerramento"):
                combined += assets["encerramento"]

            combined.export(audio_saida_path, format="mp3", bitrate="192k")
            print(f"  [OK] Audio final gerado em: {audio_saida_path}")
            
            # Copiar para AUDIO RADIO tambem
            audio_radio_path = audio_saida_path.replace("02_AUDIOS_MAILING", "03_AUDIOS_RADIO")
            os.makedirs(os.path.dirname(audio_radio_path), exist_ok=True)
            import shutil
            shutil.copy2(audio_saida_path, audio_radio_path)
            
            # Preservar o roteiro original
            print(f"  [PRESERVADO] Roteiro NJUD mantido no Drive: {txt_path}")
            return True
        except Exception as e:
            print(f"  [ERRO] Montagem final: {e}")
            return False
    else:
        # Fallback se não conseguir separar seções
        try:
            seg_bytes = await gerar_tts_com_retry(roteiro_revisado, VOZ_SPEAKER_1)
            combined = AudioSegment.from_mp3(io.BytesIO(seg_bytes))
            combined.export(audio_saida_path, format="mp3", bitrate="192k")
            
            audio_radio_path = audio_saida_path.replace("02_AUDIOS_MAILING", "03_AUDIOS_RADIO")
            os.makedirs(os.path.dirname(audio_radio_path), exist_ok=True)
            import shutil
            shutil.copy2(audio_saida_path, audio_radio_path)
            
            # Preservar o roteiro original
            print(f"  [PRESERVADO] Roteiro NJUD mantido no Drive: {txt_path}")
            return True
        except Exception as e:
            return False

async def main():
    print("=== Processador NJUD Rádio TJRN — Início ===")
    
    if not os.path.exists(ROTEIROS_DIR_NJUD):
        print(f"[INFO] Pasta não encontrada: {ROTEIROS_DIR_NJUD}")
        sys.exit(0)
        
    # Busca recursiva por roteiros de jornais nos formatos suportados
    todos_roteiros = []
    for ext in ["*.txt", "*.gdoc", "*.docx"]:
        todos_roteiros.extend(glob.glob(os.path.join(ROTEIROS_DIR_NJUD, "**", ext), recursive=True))
        
    if not todos_roteiros:
        print("[INFO] Nenhum roteiro de NJUD encontrado!")
        sys.exit(0)
 
    llm = LLMFactory()
    
    vht_abertura_path = os.path.join(GLOBAL_VHT_DIR, "NJUD - VHT - ABERTURA.mp3").replace("\\", "/")
    vht_encerramento_path = os.path.join(GLOBAL_VHT_DIR, "NJUD - VHT - ENCERRAMENTO.mp3").replace("\\", "/")
    vht_passagem_path = os.path.join(GLOBAL_VHT_DIR, "NJUD - VHT - PASSAGEM.mp3").replace("\\", "/")
    bg_trilha_path = os.path.join(GLOBAL_VHT_DIR, "NJUD - BG.mp3").replace("\\", "/")
 
    assets = {
        "abertura": carregar_audio_asset(vht_abertura_path, "Abertura"),
        "encerramento": carregar_audio_asset(vht_encerramento_path, "Encerramento"),
        "passagem": carregar_audio_asset(vht_passagem_path, "Passagem"),
        "bg_trilha": carregar_audio_asset(bg_trilha_path, "Trilha BG")
    }
 
    # Filtrar jornais que já possuem a respectiva versão em áudio (03_AUDIOS_RADIO) no Drive
    roteiros_pendentes = []
    for r in todos_roteiros:
        # Determina o caminho de áudio correspondente no Drive (03_AUDIOS_RADIO)
        audio_radio_path = r.replace("01_ROTEIROS", "03_AUDIOS_RADIO")
        for ext in [".txt", ".gdoc", ".docx"]:
            audio_radio_path = audio_radio_path.replace(ext, ".mp3")
            
        if os.path.exists(audio_radio_path):
            print(f"[PULADO] Áudio de NJUD correspondente já existe no Drive: {os.path.basename(audio_radio_path)}")
            continue
            
        roteiros_pendentes.append(r)
        
    if not roteiros_pendentes:
        print(f"\n[INFO] Todos os {len(todos_roteiros)} roteiros de NJUD já possuem áudio correspondente no Drive.")
        sys.exit(0)
        
    print(f"\n[INFO] Detectados {len(roteiros_pendentes)} novos roteiros de NJUD pendentes para produção.")
 
    sem = asyncio.Semaphore(2)
    async def processar_com_sem(path):
        async with sem:
            return await processar_jornal_local(path, assets, llm)
 
    tasks = [processar_com_sem(r) for r in roteiros_pendentes]
    results = await asyncio.gather(*tasks)
    sucessos = [res for res in results if res]
    
    print(f"\n=== PROCESSAMENTO NJUD FINALIZADO: {len(sucessos)} de {len(roteiros_pendentes)} concluídos ===")
 
if __name__ == "__main__":
    asyncio.run(main())