import os
import sqlite3
import json
import argparse
import shutil
import re
from fetch_lyrics import get_lyrics
from transcribe_audio import transcribe_audio_slice

DB_PATH = r"D:\RADIO\radio_omni.db"
QUARENTENA_DIR = r"D:\RADIO\QUARENTENA_TJ"
MUSICAS_DIR = r"D:\RADIO\MUSICAS"

def sanitize_filename(name):
    """Remove caracteres invalidos para nomes de arquivos no Windows."""
    if not name:
        return "UNKNOWN"
    # Substitui caracteres proibidos por vazio ou espaco
    for c in r'\/:*?"<>|':
        name = name.replace(c, '')
    # Substitui caracteres de controle ou tabs
    name = re.sub(r'[\x00-\x1f\x7f]', '', name)
    return " ".join(name.split()).strip()

def collect_pending_songs(limit=20):
    """
    Busca musicas nao auditadas no banco de dados e tenta obter a letra delas.
    Gera o arquivo curator_pending.json.
    """
    if not os.path.exists(DB_PATH):
        print(f"Erro: Banco de dados nao encontrado em {DB_PATH}")
        return
        
    print(f"Conectando ao banco de dados: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Seleciona as musicas onde auditado_acustica = 0
    cursor.execute("""
        SELECT id, caminho, artista, titulo, estilo, tema_especial 
        FROM musicas 
        WHERE auditado_acustica = 0 
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    if not rows:
        print("Nenhuma musica pendente de auditoria encontrada.")
        conn.close()
        return
        
    print(f"Coletando dados para {len(rows)} musica(s)...")
    pending_list = []
    
    for row in rows:
        song_id = row['id']
        caminho = row['caminho']
        artista = row['artista']
        titulo = row['titulo']
        estilo = row['estilo']
        tema = row['tema_especial']
        
        print(f"\nProcessando [{song_id}]: {artista} - {titulo}")
        print(f"Caminho: {caminho}")
        
        lyrics = None
        source = None
        
        # 1. Verifica existencia do arquivo fisico
        if not os.path.exists(caminho):
            print(f"Aviso: Arquivo fisico nao encontrado no disco. Pulando transcricao/web.")
            lyrics = "[ERRO: ARQUIVO FISICO NAO ENCONTRADO NO DISCO]"
            source = "error"
        else:
            # 2. Tenta pegar a letra na internet
            try:
                web_lyrics, web_source = get_lyrics(artista, titulo)
                if web_lyrics:
                    print(f"-> Letra obtida da internet via {web_source}!")
                    lyrics = web_lyrics
                    source = "web"
            except Exception as e:
                print(f"Erro ao buscar letra na web: {e}")
                
            # 3. Se indisponivel, transcreve com Whisper
            if not lyrics:
                print("-> Letra nao encontrada na internet. Iniciando transcricao local via Whisper...")
                try:
                    transcription = transcribe_audio_slice(caminho, limit_seconds=90)
                    if transcription:
                        print("-> Transcricao concluida com sucesso!")
                        lyrics = transcription
                        source = "transcricao"
                    else:
                        print("-> Falha na transcricao do audio.")
                        lyrics = "[ERRO: FALHA NA TRANSCRICAO E LETRA NAO ENCONTRADA]"
                        source = "error"
                except Exception as e:
                    print(f"Erro ao transcrever audio: {e}")
                    lyrics = f"[ERRO NA TRANSCRICAO: {str(e)}]"
                    source = "error"
                    
        pending_list.append({
            "id": song_id,
            "caminho_original": caminho,
            "artista_original": artista,
            "titulo_original": titulo,
            "estilo_original": estilo,
            "tema_especial_original": tema,
            "letra": lyrics,
            "fonte_letra": source
        })
        
    # Grava o arquivo JSON
    pending_file = "curator_pending.json"
    with open(pending_file, "w", encoding="utf-8") as f:
        json.dump(pending_list, f, indent=2, ensure_ascii=False)
        
    print(f"\nColeta concluida! {len(pending_list)} musicas gravadas em {pending_file}")
    conn.close()

def apply_decisions():
    """
    Le o arquivo curator_decisions.json e aplica as decisoes no disco e no banco de dados.
    """
    decisions_file = "curator_decisions.json"
    if not os.path.exists(decisions_file):
        print(f"Erro: Arquivo de decisoes {decisions_file} nao encontrado.")
        return
        
    with open(decisions_file, "r", encoding="utf-8") as f:
        decisions = json.load(f)
        
    if not decisions:
        print("Nenhuma decisao encontrada no arquivo.")
        return
        
    if not os.path.exists(DB_PATH):
        print(f"Erro: Banco de dados nao encontrado em {DB_PATH}")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Cria pasta de quarentena se nao existir
    if not os.path.exists(QUARENTENA_DIR):
        os.makedirs(QUARENTENA_DIR)
        print(f"Diretorio de quarentena criado em: {QUARENTENA_DIR}")
        
    success_count = 0
    error_count = 0
    
    for item in decisions:
        song_id = item.get("id")
        caminho_orig = item.get("caminho_original")
        status = item.get("status") # APROVADO ou REPROVADO
        motivo = item.get("motivo", "")
        
        # Dados corrigidos da IA
        artista_corr = item.get("artista_correto", item.get("artista_original"))
        titulo_corr = item.get("titulo_correto", item.get("titulo_original"))
        estilo_corr = item.get("estilo_correto", item.get("estilo_original"))
        tema_corr = item.get("tema_especial", item.get("tema_especial_original"))
        
        if not status or not song_id:
            print(f"Aviso: Decisao invalida para o item {item}. Pulando.")
            error_count += 1
            continue
            
        print(f"\nAplicando decisao para [{song_id}]: {artista_corr} - {titulo_corr} ({status})")
        
        # 1. Verifica se arquivo original existe
        if not os.path.exists(caminm_orig := caminho_orig):
            # Se for erro de arquivo que nao existe, mas o status for APROVADO/REPROVADO, 
            # podemos tentar apenas atualizar o banco ou pular se o arquivo sumiu.
            print(f"Erro: Arquivo fisico nao encontrado em {caminho_orig}")
            # Atualiza apenas o banco marcando como auditado mas com erro de arquivo
            try:
                cursor.execute("""
                    UPDATE musicas 
                    SET auditado_acustica = 1, ai_insight = ? 
                    WHERE id = ?
                """, (f"Arquivo fisico nao encontrado. {motivo}", song_id))
                success_count += 1
            except Exception as e:
                print(f"Erro ao atualizar banco: {e}")
                error_count += 1
            continue
            
        # Nomes higienizados para o arquivo fisico
        art_clean = sanitize_filename(artista_corr)
        tit_clean = sanitize_filename(titulo_corr)
        ext = os.path.splitext(caminho_orig)[1].lower()
        filename = f"{art_clean} - {tit_clean}{ext}"
        
        if status == "APROVADO":
            # Determina o diretorio de destino baseado no tema especial
            dir_orig = os.path.dirname(caminho_orig)
            # Se a musica pertencer a um tema especial (como junho), garantimos a pasta especial_junho
            if tema_corr and tema_corr.strip().lower() == "junho":
                # Se o diretorio nao contiver ESPECIAL_JUNHO no caminho, movemos para la
                dest_dir = os.path.join(MUSICAS_DIR, "ESPECIAL_JUNHO")
            else:
                dest_dir = dir_orig # Mantem no diretorio original
                
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
                
            caminho_dest = os.path.join(dest_dir, filename)
            
            # Move/Renomeia o arquivo fisico se o caminho for diferente
            # Normaliza caminhos para comparacao
            if os.path.normpath(caminho_orig) != os.path.normpath(caminho_dest):
                try:
                    # Se o destino ja existir, remove para nao falhar
                    if os.path.exists(caminho_dest):
                        os.remove(caminho_dest)
                    shutil.move(caminho_orig, caminho_dest)
                    print(f"Arquivo renomeado para: {caminho_dest}")
                except Exception as e:
                    print(f"Erro ao mover arquivo: {e}")
                    error_count += 1
                    continue
            else:
                caminho_dest = caminho_orig
                print("Arquivo ja esta na pasta e nomenclatura corretas.")
                
            # Atualiza o banco de dados
            try:
                cursor.execute("""
                    UPDATE musicas
                    SET caminho = ?, artista = ?, titulo = ?, estilo = ?, tema_especial = ?, 
                        auditado_acustica = 1, redflag = 0, ai_insight = ?, quarantine_reason = NULL
                    WHERE id = ?
                """, (caminho_dest, artista_corr, titulo_corr, estilo_corr, tema_corr, motivo, song_id))
                success_count += 1
            except Exception as e:
                print(f"Erro ao atualizar registro no banco: {e}")
                error_count += 1
                
        elif status == "REPROVADO":
            # Move o arquivo para a quarentena
            caminho_dest = os.path.join(QUARENTENA_DIR, filename)
            try:
                if os.path.exists(caminho_dest):
                    os.remove(caminho_dest)
                shutil.move(caminho_orig, caminho_dest)
                print(f"Musica movida para quarentena: {caminho_dest}")
            except Exception as e:
                print(f"Erro ao mover arquivo para quarentena: {e}")
                error_count += 1
                continue
                
            # Atualiza o banco de dados
            try:
                cursor.execute("""
                    UPDATE musicas
                    SET caminho = ?, artista = ?, titulo = ?, estilo = ?, tema_especial = ?, 
                        auditado_acustica = 1, redflag = 1, quarantine_reason = ?, ai_insight = ?
                    WHERE id = ?
                """, (caminho_dest, artista_corr, titulo_corr, estilo_corr, tema_corr, motivo, motivo, song_id))
                success_count += 1
            except Exception as e:
                print(f"Erro ao atualizar registro no banco: {e}")
                error_count += 1
                
    conn.commit()
    conn.close()
    
    print(f"\nAplicacao de decisoes concluida!")
    print(f"Sucesso: {success_count} | Erro: {error_count}")
    
    # Limpa os arquivos JSON temporarios
    try:
        if os.path.exists(decisions_file):
            os.remove(decisions_file)
        pending_file = "curator_pending.json"
        if os.path.exists(pending_file):
            os.remove(pending_file)
        print("Arquivos JSON temporarios limpos.")
    except Exception as e:
        print(f"Aviso ao limpar arquivos temporarios: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerenciador de Curadoria Profunda de Letras")
    parser.add_argument("--collect", action="store_true", help="Coleta musicas pendentes e busca letras/transcreve")
    parser.add_argument("--apply", action="store_true", help="Aplica decisoes do arquivo curator_decisions.json")
    parser.add_argument("--limit", type=int, default=20, help="Limite de musicas para coletar (padrao: 20)")
    
    args = parser.parse_args()
    
    if args.collect:
        collect_pending_songs(args.limit)
    elif args.apply:
        apply_decisions()
    else:
        parser.print_help()
