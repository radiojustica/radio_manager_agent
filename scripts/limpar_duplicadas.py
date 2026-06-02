import os
import sqlite3
from collections import defaultdict
from pathlib import Path

# Configurações
DB_PATH = r"D:\RADIO\radio_omni.db"
# True: Apaga o arquivo físico extra do HD. False: Apenas remove do banco de dados (Soft Clean)
APAGAR_DO_DISCO = True 

def limpar_duplicadas():
    if not os.path.exists(DB_PATH):
        print(f"Banco de dados não encontrado em {DB_PATH}")
        return

    print("Iniciando varredura por faixas duplicadas...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Agrupa por título e artista e pega todos os caminhos e IDs associados
    cursor.execute("""
        SELECT titulo, artista, id, caminho 
        FROM musicas 
        ORDER BY titulo, artista
    """)
    
    todas_musicas = cursor.fetchall()
    
    # Dicionário para mapear (titulo, artista) -> lista de dicts com id e caminho
    agrupadas = defaultdict(list)
    for titulo, artista, m_id, caminho in todas_musicas:
        agrupadas[(titulo, artista)].append({
            "id": m_id,
            "caminho": caminho
        })

    ids_para_remover = []
    arquivos_para_apagar = []
    
    for (titulo, artista), faixas in agrupadas.items():
        if len(faixas) > 1:
            print(f"\nDetectado {len(faixas)} cópias de: {artista} - {titulo}")
            
            # Vamos manter a PRIMEIRA faixa que realmente exista no disco
            faixa_mantida = None
            
            for f in faixas:
                if os.path.exists(f["caminho"]):
                    if faixa_mantida is None:
                        # Achamos uma versão válida no disco, essa é a oficial
                        faixa_mantida = f
                        print(f"  [MANTIDA] {f['caminho']}")
                    else:
                        # Já temos uma oficial. Esta é duplicada real (ou duplicada no banco).
                        ids_para_remover.append(f["id"])
                        print(f"  [DESCARTADA] {f['caminho']}")
                        # Se o arquivo também existir no disco e não for exatamente o mesmo caminho da oficial
                        if os.path.exists(f["caminho"]) and f["caminho"] != faixa_mantida["caminho"]:
                            arquivos_para_apagar.append(f["caminho"])
                else:
                    # Registro fantasma (arquivo não existe mais no disco)
                    ids_para_remover.append(f["id"])
                    print(f"  [FANTASMA] {f['caminho']} (Será removida do DB)")
                    
            # Caso extremo: nenhuma delas existe no disco. Limpamos todas.
            if faixa_mantida is None:
                for f in faixas:
                    if f["id"] not in ids_para_remover:
                        ids_para_remover.append(f["id"])

    if not ids_para_remover:
        print("\nNenhuma duplicata precisou ser removida. Banco limpo!")
        conn.close()
        return

    print(f"\nRESUMO: {len(ids_para_remover)} registros duplicados/fantasmas encontrados.")
    
    # 1. Remover do Banco de Dados
    print(f"Apagando {len(ids_para_remover)} registros do banco de dados SQLite...")
    placeholders = ",".join("?" * len(ids_para_remover))
    cursor.execute(f"DELETE FROM musicas WHERE id IN ({placeholders})", ids_para_remover)
    conn.commit()
    
    # 2. Apagar fisicamente do disco (Opcional, com base na flag)
    if arquivos_para_apagar:
        print(f"Detectados {len(arquivos_para_apagar)} arquivos físicos redundantes no disco.")
        if APAGAR_DO_DISCO:
            for caminho in arquivos_para_apagar:
                try:
                    os.remove(caminho)
                    print(f"Removido: {caminho}")
                except Exception as e:
                    print(f"Falha ao remover arquivo {caminho}: {e}")
            print("Limpeza de arquivos físicos concluída.")
        else:
            print("APAGAR_DO_DISCO está False. Os arquivos extras foram removidos do banco de dados, mas permanecem no HD.")
            
    conn.close()
    print("Processo finalizado.")

if __name__ == "__main__":
    limpar_duplicadas()
