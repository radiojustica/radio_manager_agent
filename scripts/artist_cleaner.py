import os
import re

def clean_artist_name(artista, caminho):
    """
    Tenta limpar e extrair o nome do artista de forma robusta.
    Se o artista for 'Desconhecido' ou vazio, tenta extrair do nome do arquivo.
    """
    if not artista or str(artista).strip().lower() in ["desconhecido", "unknown", "various"]:
        # Tenta extrair do nome do arquivo
        nome_arquivo = os.path.basename(caminho)
        # Remove a extensão
        nome_arquivo = os.path.splitext(nome_arquivo)[0]
        
        # Padrões comuns: "Artista - Titulo", "ARTISTA-TITULO", "ARTISTA - TITULO"
        if " - " in nome_arquivo:
            parts = nome_arquivo.split(" - ")
            artista = parts[0]
        elif "-" in nome_arquivo:
            # Cuidado com hifens no meio de palavras, pegamos a primeira parte
            parts = nome_arquivo.split("-")
            artista = parts[0]
        else:
            artista = nome_arquivo

    if not artista:
        return "VARIOUS"

    # Normalização final
    artista = str(artista).upper().strip()
    # Remove caracteres especiais comuns
    artista = re.sub(r'[^\w\s&]', '', artista)
    return artista


