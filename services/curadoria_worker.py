import os
import multiprocessing
import numpy as np
import unicodedata
import re
import shutil
import json
from datetime import datetime

PASTA_QUARENTENA = r"D:\RADIO\QUARENTENA_TJ"

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
        except:
            pass
    return ["puta", "safadao", "baroes da pisadinha"] # Fallback

def verificar_inadequacao(nome_arquivo):
    check_str = remover_acentos(nome_arquivo)
    regras = carregar_badwords()
    return any(re.search(fr"\b{p}\b" if len(p) < 15 else p, check_str) for p in regras)

def calcular_energia_librosa(caminho):
    """
    Função pesada isolada. Somente importamos o Librosa DENTRO do worker
    para evitar overhead global na RAM do Servidor REST.
    """
    import librosa
    try:
        y, sr = librosa.load(caminho, sr=22050, offset=20.0, duration=5.0)
        rms = np.mean(librosa.feature.rms(y=y))
        centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
        
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

        if pontos <= 30: return 1      
        elif pontos <= 50: return 2    
        elif pontos <= 70: return 3    
        elif pontos <= 85: return 4    
        else: return 5                 
    except Exception as e:
        print(f"[WORKER] Falha acústica em {caminho}: {e}")
        return 3

LOG_QUARENTENA = os.path.join(PASTA_QUARENTENA, "audit_quarentena.log")

def registrar_log_quarentena(arquivo, motivo):
    """Registra a movimentação de arquivos para a quarentena."""
    os.makedirs(PASTA_QUARENTENA, exist_ok=True)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open(LOG_QUARENTENA, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] ARQUIVO: {arquivo} | MOTIVO: {motivo}\n")
    except Exception as e:
        print(f"Erro ao escrever log de quarentena: {e}")

def processar_arquivo(id_musica, caminho):
    """Verifica quarentena por badwords ou corrupção, calcula energia e duração."""
    from mutagen import File
    import librosa
    nome_arq = os.path.basename(caminho)
    duracao = 210 # fallback
    
    # 1. VERIFICAÇÃO DE INTEGRIDADE (ARQUIVO CORROMPIDO)
    try:
        audio = File(caminho)
        if not audio or not audio.info:
            raise ValueError("Arquivo ilegível por Mutagen")
        duracao = int(audio.info.length)
        
        # Teste de carregamento librosa (se falhar, está corrompido para o player também)
        y, sr = librosa.load(caminho, sr=22050, offset=2.0, duration=2.0)
    except Exception as e:
        registrar_log_quarentena(nome_arq, f"CORROMPIDO/ILEGÍVEL: {str(e)}")
        os.makedirs(PASTA_QUARENTENA, exist_ok=True)
        try:
            shutil.move(caminho, os.path.join(PASTA_QUARENTENA, nome_arq))
            return {"id": id_musica, "status": "QUARANTINED", "motivo": "Corrompido", "energia": 3, "duracao": duracao}
        except Exception as move_err:
            return {"id": id_musica, "status": "ERROR_MOVE", "energia": 3, "duracao": duracao}

    # 2. VERIFICAÇÃO DE BADWORDS (INADEQUAÇÃO)
    if verificar_inadequacao(nome_arq):
        registrar_log_quarentena(nome_arq, "BADWORD/INADEQUAÇÃO DETECTADA")
        os.makedirs(PASTA_QUARENTENA, exist_ok=True)
        try:
            shutil.move(caminho, os.path.join(PASTA_QUARENTENA, nome_arq))
            return {"id": id_musica, "status": "QUARANTINED", "motivo": "Inadequação", "energia": 3, "duracao": duracao}
        except:
            return {"id": id_musica, "status": "ERROR_MOVE", "energia": 3, "duracao": duracao}
            
    # 3. CÁLCULO DE ENERGIA (Para músicas saudáveis)
    # Baixa energia NÃO é mais motivo de quarentena.
    energia = calcular_energia_librosa(caminho)
    return {"id": id_musica, "status": "OK", "energia": energia, "duracao": duracao}

def _job_processar_lote(lote_musicas):
    from core.database import SessionLocal
    from core.models import Musica
    
    status_path = os.path.join(os.path.dirname(__file__), "worker_status.txt")
    with open(status_path, "w", encoding="utf-8") as f:
        f.write("Iniciando lote...")

    db = SessionLocal()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [WORKER] Iniciando processamento de {len(lote_musicas)} faixas pendentes no background...")
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
                if resultado["status"] == "QUARANTINED":
                    musica_db.redflag = True
                else:
                    musica_db.energia = resultado["energia"]
                
                musica_db.duracao = resultado["duracao"]
                db.commit()
                
        with open(status_path, "w", encoding="utf-8") as f:
            f.write("Ocioso (Próximo ciclo em 5 min)")
            
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [WORKER] Lote de auditoria acústica concluído.")
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


