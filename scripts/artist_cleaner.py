import os
import re

# Padrões que indicam que o "artista" foi empurrado para o título e o campo
# artista está vazio/desconhecido. Nesses casos extraímos do nome do arquivo.
_ARTISTA_DESCONHECIDO = {"desconhecido", "unknown", "various", "", "none", "n/a"}

# Conectivos comuns em nomes de arquivo que NÃO são parte do artista
# (usados para limpar sufixos como " - Ao Vivo", " - Remix", etc.)
_SUFIXOS_RUÍDO = re.compile(
    r"\s*-\s*(ao vivo|live|remix|remaster| versao|versão|acustico|acústico|"
    r"radio edit|explicit|deluxe|edicao|edição|internacional|national|"
    r"part\.|part|feat\.?|ft\.?)\b.*$",
    re.IGNORECASE,
)

# Variações de "e"/"&" para normalização
_AMP = re.compile(r"\s*&\s*|\s+e\s+", re.IGNORECASE)


def _normalizar(texto: str) -> str:
    """Caixa alta, sem acentos, sem pontuação — para comparação estável."""
    if not texto:
        return ""
    t = texto.upper().strip()
    # Remove acentos
    t = re.sub(r"[ÀÁÂÃÄ]", "A", t)
    t = re.sub(r"[ÈÉÊË]", "E", t)
    t = re.sub(r"[ÌÍÎÏ]", "I", t)
    t = re.sub(r"[ÒÓÔÕÖ]", "O", t)
    t = re.sub(r"[ÙÚÛÜ]", "U", t)
    t = re.sub(r"[Ç]", "C", t)
    # Remove pontuação que não seja & ou espaço
    t = re.sub(r"[^\w\s&]", "", t)
    t = _AMP.sub(" E ", t)
    # Colapsa espaços
    t = re.sub(r"\s+", " ", t).strip()
    return t


def clean_artist_name(artista, caminho):
    """
    Extrai um nome de artista NORMALIZADO e estável para deduplicação.

    Regras:
      1. Se o campo 'artista' for válido (não desconhecido), usa-o, limpando
         sufixos de edição (Ao Vivo, Remix...) e normalizando.
      2. Caso contrário (artista desconhecido/vazio), extrai a PRIMEIRA parte
         antes do separador ' - ' no nome do arquivo — que é o padrão
         'ARTISTA - TÍTULO' usado pela rádio. NÃO inclui o título.
      3. Normaliza caixa/acentos/pontuação para que 'IVANDO' e 'IVANILDO'
         (ou 'Camaroes' vs 'Camarões') sejam tratados de forma consistente.

    IMPORTANTE: retorna apenas o ARTISTA, nunca o título da música. Isso é
    o que permite ao GestorFila impedir repetição de ARTISTA.
    """
    nome_arquivo = os.path.basename(str(caminho) if caminho else "")
    nome_arquivo = os.path.splitext(nome_arquivo)[0]

    raw = None
    if artista and str(artista).strip().lower() not in _ARTISTA_DESCONHECIDO:
        raw = str(artista)
    else:
        # Tenta extrair do nome do arquivo: ARTISTA - TÍTULO
        if " - " in nome_arquivo:
            raw = nome_arquivo.split(" - ", 1)[0]
        elif " -" in nome_arquivo:
            raw = nome_arquivo.split(" -", 1)[0]
        elif "-" in nome_arquivo:
            # Hifen único: pega a primeira parte (cuidado com hifens em palavras)
            parts = nome_arquivo.split("-")
            raw = parts[0]
        else:
            raw = nome_arquivo

    if not raw or not raw.strip():
        return "VARIOUS"

    # Limpa sufixos de edição que porventura tenham grudado
    raw = _SUFIXOS_RUÍDO.sub("", raw)
    raw = raw.strip(" -")

    return _normalizar(raw) or "VARIOUS"
