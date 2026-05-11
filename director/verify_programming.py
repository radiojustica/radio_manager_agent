import os
import sys
import json
import logging
from datetime import datetime

# Adiciona o diretório base ao sys.path para importar os módulos locais
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.artist_cleaner import clean_artist_name

# Configurações de Auditoria
MAX_REPETICOES_ARTISTA_1H = 1 # Mais de 1 repetição (ou seja, 2 ocorrências) é violação
JANELA_MUSICAS_AUDITORIA = 30 # Aproximadamente 1h e 45min (30 músicas de 3.5min)

def audit_m3u(file_path):
    violations = []
    if not os.path.exists(file_path):
        return violations

    try:
        with open(file_path, "r", encoding="cp1252", errors="ignore") as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
        
        # Filtra apenas músicas (ignora vinhetas, spots, boletins se possível, 
        # mas aqui vamos auditar tudo que parecer música pelo caminho)
        musicas = [l for l in lines if r"D:\RADIO\MUSICAS" in l.upper()]
        
        for i in range(len(musicas)):
            window = musicas[i:i + JANELA_MUSICAS_AUDITORIA]
            if not window: break
            
            artistas_na_janela = []
            for m_path in window:
                # Extrai artista do caminho (fallback se não tiver DB aqui)
                nome_base = os.path.basename(m_path)
                artista = clean_artist_name(None, m_path)
                artistas_na_janela.append(artista)
            
            # Conta repetições
            counts = {}
            for art in artistas_na_janela:
                if art == "VARIOUS": continue
                counts[art] = counts.get(art, 0) + 1
                if counts[art] > MAX_REPETICOES_ARTISTA_1H:
                    violations.append({
                        "artista": art,
                        "posicao": i,
                        "arquivo": os.path.basename(file_path),
                        "contexto": f"Artista '{art}' repete {counts[art]} vezes em uma janela de {len(window)} músicas."
                    })
                    # Registra apenas uma vez por janela para evitar spam
                    break
        
    except Exception as e:
        print(f"Erro ao auditar {file_path}: {e}")
        
    return violations

def run_daily_audit():
    print(f"[{datetime.now()}] Iniciando Auditoria de Programação...")
    folder = r"D:\RADIO\PROGRAMACAO"
    if not os.path.exists(folder):
        print(f"Pasta de programação não encontrada: {folder}")
        return

    m3us = [os.path.join(folder, f) for f in os.listdir(folder) if f.startswith("PROG_") and f.endswith(".m3u")]
    
    total_violations = 0
    files_to_redo = []

    for m3u in m3us:
        violations = audit_m3u(m3u)
        if violations:
            print(f"⚠️ VIOLAÇÕES ENCONTRADAS em {os.path.basename(m3u)}:")
            for v in violations:
                print(f"  - {v['contexto']}")
            total_violations += len(violations)
            files_to_redo.append(m3u)

    if total_violations > 0:
        print(f"\nTotal de {total_violations} violações críticas detectadas.")
        print("Ação sugerida: Refazer as grades afetadas.")
        return files_to_redo
    else:
        print("\n✅ Nenhuma violação de regra de artista detectada nos blocos atuais.")
        return []

if __name__ == "__main__":
    run_daily_audit()


