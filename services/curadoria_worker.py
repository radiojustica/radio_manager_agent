import os
import multiprocessing

import unicodedata
import re
import shutil
import json
from datetime import datetime
from core.time_utils import now_local

# Importa normalizador de ID3 (compatibilidade com ZaraRadio)
try:
    from scripts.fix_id3_encoding import normalizar_id3_arquivo as _normalizar_id3
    _ID3_FIXER_DISPONIVEL = True
except ImportError:
    _ID3_FIXER_DISPONIVEL = False

PASTA_QUARENTENA = r"D:\RADIO\QUARENTENA_TJ"

# Pasta raiz padrão do acervo musical (fallback se settings.json não carregar)
_PASTA_MUSICAS_PADRAO = r"D:\RADIO\MUSICAS"


def _get_pasta_musicas() -> str:
    """Retorna a pasta de músicas configurada (lê settings.json ou usa o padrão)."""
    try:
        from core.config_loader import get_settings
        return get_settings().get("grade", {}).get("pasta_musicas", _PASTA_MUSICAS_PADRAO)
    except Exception:
        return _PASTA_MUSICAS_PADRAO


def _arquivo_em_pasta_musicas(caminho: str) -> bool:
    """
    Verifica se o arquivo pertence à pasta de músicas autorizada.
    PROTEÇÃO DE SEGURANÇA: impede que arquivos fora do acervo sejam
    movidos acidentalmente para a quarentena.
    """
    norm_caminho = os.path.normpath(os.path.abspath(caminho))
    norm_pasta = os.path.normpath(os.path.abspath(_get_pasta_musicas()))
    # Aceita também arquivos já na quarentena (para evitar falha em reprocessamento)
    norm_quarentena = os.path.normpath(os.path.abspath(PASTA_QUARENTENA))
    return norm_caminho.startswith(norm_pasta + os.sep) or norm_caminho.startswith(norm_quarentena + os.sep)

def remover_acentos(texto):
    """Remove acentos e caracteres especiais de uma string."""
    if not texto: return ""
    return "".join(c for c in unicodedata.normalize('NFD', texto)
                  if unicodedata.category(c) != 'Mn').lower()

def carregar_badwords():
    """Carrega a lista de termos proibidos do arquivo JSON."""
    badwords_path = "config/badwords.json"
    if os.path.exists(badwords_path):
        try:
            with open(badwords_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return ["puta", "safadao", "baroes da pisadinha"] # Fallback

def verificar_inadequacao(nome_arquivo):
    check_str = remover_acentos(nome_arquivo)
    regras = carregar_badwords()
    return any(re.search(fr"\b{p}\b" if len(p) < 15 else p, check_str) for p in regras)

def analisar_acustica_completa(caminho):
    import numpy as np
    """
    Analisa BPM, Energia, Valência e Dançabilidade usando Librosa.
    Heurísticas avançadas para determinar a 'vibe' da música.
    """
    import librosa
    try:
        # Carregamos 15 segundos (offset 20s) para uma amostra mais representativa
        y, sr = librosa.load(caminho, sr=22050, offset=20.0, duration=15.0)
        
        # 1. Energia (Baseado em RMS e Centroid Espectral)
        rms = np.mean(librosa.feature.rms(y=y))
        centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
        flatness = float(np.mean(librosa.feature.spectral_flatness(y=y)))
        
        pontos = 0
        if rms > 0.22: pontos += 50
        elif rms > 0.15: pontos += 40
        elif rms > 0.09: pontos += 30
        elif rms > 0.05: pontos += 20
        else: pontos += 10

        if centroid > 2500: pontos += 50
        elif centroid > 1800: pontos += 40
        elif centroid > 1200: pontos += 30
        elif centroid > 800: pontos += 20
        else: pontos += 10

        energia_score = 3
        if pontos <= 30: energia_score = 1      
        elif pontos <= 50: energia_score = 2    
        elif pontos <= 70: energia_score = 3    
        elif pontos <= 85: energia_score = 4    
        else: energia_score = 5

        # 2. BPM (Beat Tracking mais preciso)
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        tempo, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
        bpm = int(tempo.item()) if hasattr(tempo, "item") else int(tempo)

        # 3. Valence (Heurística: Brilho + Estabilidade + Energia)
        # Músicas "felizes/positivas" tendem a ser brilhantes e rítmicas
        norm_centroid = min(centroid / 5000.0, 1.0)
        norm_rms = min(rms / 0.4, 1.0)
        valence = (norm_centroid * 0.4 + norm_rms * 0.4 + (1.0 - flatness) * 0.2)

        # 4. Danceability (Heurística: Força e Regularidade do Ritmo via Tempograma)
        # Usamos a média do tempograma como proxy para a força rítmica perceptível
        tg = librosa.feature.tempogram(onset_envelope=onset_env, sr=sr)
        dance_score = float(np.mean(tg[1:4, :])) # Focamos nas frequências de pulso baixas
        danceability = min(dance_score * 5.0, 1.0) # Normalização para escala 0-1

        return {
            "energia": energia_score,
            "bpm": bpm,
            "valence": round(float(valence), 2),
            "danceability": round(float(danceability), 2),
            "flatness": round(flatness, 4)
        }
    except Exception as e:
        print(f"[WORKER] Falha acústica completa em {caminho}: {e}")
        return {"energia": 3, "bpm": 0, "valence": 0.5, "danceability": 0.5, "flatness": 0.0}

LOG_QUARENTENA = os.path.join(PASTA_QUARENTENA, "audit_quarentena.log")

def registrar_log_quarentena(arquivo, motivo):
    """Registra a movimentação de arquivos para a quarentena."""
    os.makedirs(PASTA_QUARENTENA, exist_ok=True)
    timestamp = now_local().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open(LOG_QUARENTENA, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] ARQUIVO: {arquivo} | MOTIVO: {motivo}\n")
    except Exception as e:
        print(f"Erro ao escrever log de quarentena: {e}")

def processar_arquivo(id_musica, caminho):
    """Verifica quarentena por badwords, corrupção e métricas avançadas (Librosa).
    Inclui normalização automática de tags ID3 para compatibilidade com ZaraRadio.
    """
    from mutagen import File
    import librosa
    nome_arq = os.path.basename(caminho)
    duracao = 210 # fallback
    
    # 0. NORMALIZAÇÃO DE TAGS ID3 (ENCODING PARA cp1252/Latin-1)
    # Garante compatibilidade com ZaraRadio que exibe em Windows-1252
    if _ID3_FIXER_DISPONIVEL and os.path.exists(caminho):
        try:
            resultado_id3 = _normalizar_id3(caminho, dry_run=False)
            if resultado_id3.get("status") == "alterado":
                import logging
                logging.getLogger("OmniCore.CuradoriaService").info(
                    f"[ID3] Tags normalizadas para cp1252 em: {nome_arq}"
                )
        except Exception as e:
            import logging
            logging.getLogger("OmniCore.CuradoriaService").warning(
                f"[ID3] Falha na normalização de tags em '{nome_arq}': {e}"
            )
    
    # VERIFICAÇÃO DE SEGURANÇA: arquivo deve estar na pasta de músicas autorizada
    if not _arquivo_em_pasta_musicas(caminho):
        import logging as _log
        _log.getLogger("OmniCore.CuradoriaService").error(
            f"[SEGURANÇA] Tentativa de mover arquivo fora da pasta de músicas bloqueada: {caminho}"
        )
        return {"id": id_musica, "status": "ERROR", "motivo": "Arquivo fora da pasta de músicas autorizada — operação bloqueada.", "energia": 3, "duracao": duracao, "bpm": 0, "valence": 0.5, "danceability": 0.5}

    # 1. VERIFICAÇÃO DE INTEGRIDADE (ARQUIVO CORROMPIDO)
    try:
        audio = File(caminho)
        if not audio or not audio.info:
            raise ValueError("Arquivo ilegível por Mutagen")
        duracao = int(audio.info.length)
        
        # Teste rápido de carregamento librosa
        librosa.load(caminho, sr=22050, offset=2.0, duration=1.0)
    except Exception as e:
        registrar_log_quarentena(nome_arq, f"CORROMPIDO/ILEGÍVEL: {str(e)}")
        os.makedirs(PASTA_QUARENTENA, exist_ok=True)
        try:
            shutil.move(caminho, os.path.join(PASTA_QUARENTENA, nome_arq))
            return {"id": id_musica, "status": "QUARANTINED", "motivo": "Corrompido", "energia": 3, "duracao": duracao, "bpm": 0, "valence": 0.5, "danceability": 0.5}
        except Exception as move_err:
            return {"id": id_musica, "status": "ERROR_MOVE", "energia": 3, "duracao": duracao, "bpm": 0, "valence": 0.5, "danceability": 0.5}

    # 2. VERIFICAÇÃO DE BADWORDS (INADEQUAÇÃO)
    if verificar_inadequacao(nome_arq):
        registrar_log_quarentena(nome_arq, "BADWORD/INADEQUAÇÃO DETECTADA")
        os.makedirs(PASTA_QUARENTENA, exist_ok=True)
        try:
            shutil.move(caminho, os.path.join(PASTA_QUARENTENA, nome_arq))
            return {"id": id_musica, "status": "QUARANTINED", "motivo": "Inadequação", "energia": 3, "duracao": duracao, "bpm": 0, "valence": 0.5, "danceability": 0.5}
        except Exception:
            return {"id": id_musica, "status": "ERROR_MOVE", "energia": 3, "duracao": duracao, "bpm": 0, "valence": 0.5, "danceability": 0.5}
            
    # 3. ANÁLISE ACÚSTICA COMPLETA
    analise = analisar_acustica_completa(caminho)
    
    # 4. QUARENTENA POR QUALIDADE TÉCNICA E MÉTRICAS AVANÇADAS
    motivo_q = None
    if analise["energia"] < 2:
        motivo_q = "Baixa Energia (E1)"
    elif analise.get("flatness", 0) > 0.5:
        motivo_q = f"Ruído Excessivo (Flatness: {analise.get('flatness')})"
    elif analise["danceability"] < 0.3:
        motivo_q = f"Baixa Dançabilidade ({analise['danceability']})"
    elif analise["valence"] < 0.1:
        motivo_q = f"Valência Negativa/Melancólica ({analise['valence']})"
    elif duracao < 30:
        motivo_q = f"Duração Insuficiente ({duracao}s)"
        
    if motivo_q:
        registrar_log_quarentena(nome_arq, f"QUARENTENA: {motivo_q}")
        os.makedirs(PASTA_QUARENTENA, exist_ok=True)
        try:
            shutil.move(caminho, os.path.join(PASTA_QUARENTENA, nome_arq))
            return {
                "id": id_musica, 
                "status": "QUARANTINED", 
                "motivo": motivo_q, 
                "energia": analise["energia"], 
                "duracao": duracao, 
                "bpm": analise["bpm"], 
                "valence": analise["valence"], 
                "danceability": analise["danceability"]
            }
        except Exception:
            pass

    return {
        "id": id_musica, 
        "status": "OK", 
        "energia": analise["energia"], 
        "bpm": analise["bpm"],
        "valence": analise["valence"],
        "danceability": analise["danceability"],
        "duracao": duracao
    }

def _job_processar_lote(lote_musicas):
    import numpy as np
    from core.database import SessionLocal
    from core.models import Musica
    
    status_path = os.path.join(os.path.dirname(__file__), "worker_status.txt")
    with open(status_path, "w", encoding="utf-8") as f:
        f.write("Iniciando lote...")

    db = SessionLocal()
    print(f"[{now_local().strftime('%H:%M:%S')}] [WORKER] Iniciando processamento de {len(lote_musicas)} faixas pendentes no background...")
    try:
        total = len(lote_musicas)
        for i, (m_id, caminho) in enumerate(lote_musicas):
            nome = os.path.basename(caminho)
            with open(status_path, "w", encoding="utf-8") as f:
                f.write(f"Analisando [{i+1}/{total}]: {nome}")
                
            resultado = processar_arquivo(m_id, caminho)
            
            musica_db = db.query(Musica).filter(Musica.id == resultado["id"]).first()
            if musica_db:
                musica_db.auditado_acustica = True
                if resultado.get("status") == "QUARANTINED":
                    musica_db.redflag = True
                    musica_db.quarantine_reason = resultado.get("motivo", "Desconhecido")
                else:
                    musica_db.energia = resultado["energia"]
                    musica_db.redflag = False
                    musica_db.quarantine_reason = None
                
                musica_db.duracao = resultado["duracao"]
                musica_db.bpm = resultado["bpm"]
                musica_db.valence = resultado["valence"]
                musica_db.danceability = resultado["danceability"]
                db.commit()
                
        with open(status_path, "w", encoding="utf-8") as f:
            f.write("Ocioso (Próximo ciclo em 5 min)")
            
        print(f"[{now_local().strftime('%H:%M:%S')}] [WORKER] Lote de auditoria acústica concluído.")
    except Exception as e:
        print(f"[WORKER] Erro crítico no worker: {e}")
        with open(status_path, "w", encoding="utf-8") as f:
            f.write(f"Erro: {str(e)[:20]}...")
    finally:
        db.close()

class CuradoriaManager:
    """Invoca processos assíncronos e puros fora da thread princiapal (livrando o FastAPI)."""
    @staticmethod
    def iniciar_worker():
        from core.database import SessionLocal
        from core.models import Musica
        db = SessionLocal()
        try:
            # Pega as 10 primeiras que precisam de auditoria (ordem cronológica de cadastro)
            pendentes = db.query(Musica).filter(Musica.auditado_acustica == False).order_by(Musica.id.asc()).limit(10).all()
            if pendentes:
                lote = [(p.id, p.caminho) for p in pendentes]
                # Executa num Process Native do Windows
                p = multiprocessing.Process(target=_job_processar_lote, args=(lote,))
                p.start()
            else:
                # Opcional: registrar em log que não há pendências
                pass
        finally:
            db.close()


