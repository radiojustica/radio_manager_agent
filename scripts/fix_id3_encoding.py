"""
fix_id3_encoding.py — Omni Core
================================
Script de migração única para normalizar encoding de tags ID3 em todo o acervo.

PROBLEMA:
  ZaraRadio (Windows) usa Windows-1252 (cp1252/Latin-1) para exibir tags ID3v2.3.
  Arquivos com tags gravadas em UTF-8 (ID3v2.4 ou ID3v2.3+UTF8) aparecem
  como mojibake na janela do ZaraRadio:
    "MÃ¡rcia" em vez de "Márcia"
    "EmissÃ£o" em vez de "Emissão"

SOLUÇÃO:
  Reescreve as tags TITLE, ARTIST, ALBUM de cada arquivo MP3:
  1. Lê o valor atual via mutagen (detecta encoding interno)
  2. Normaliza o texto para NFC (forma composta, mais compatível)
  3. Regrava as tags forçando o frame ID3v2.3 com encoding Latin-1 (0x00)

USO:
  python scripts/fix_id3_encoding.py [--pasta D:\\RADIO\\MUSICAS] [--dry-run]

  --dry-run: apenas lista o que seria alterado, sem modificar arquivos.
"""

import os
import sys
import argparse
import unicodedata
import logging
from pathlib import Path

# Força UTF-8 no terminal Windows para exibir nomes de músicas corretamente
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/fix_id3_encoding.log", encoding="utf-8")
    ]
)

logger = logging.getLogger("fix_id3_encoding")

AUDIO_EXTENSIONS = {".mp3"}

def detectar_pasta_musicas() -> str:
    """Lê a pasta de músicas do settings.json."""
    try:
        import json
        with open(os.path.join("config", "settings.json"), "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("grade", {}).get("pasta_musicas", r"D:\RADIO\MUSICAS")
    except Exception:
        return r"D:\RADIO\MUSICAS"

def normalizar_tag_texto(texto: str) -> str:
    """Normaliza a string para NFC Unicode (forma canônica composta)."""
    if not texto:
        return texto
    return unicodedata.normalize("NFC", texto.strip())

def tem_mojibake(texto: str) -> bool:
    """
    Detecta padrões específicos de mojibake UTF-8 lido como Latin-1.
    Sequencias reais: UTF-8 multi-byte mapeado para Latin-1 produz pares como:
      'a' (U+00E1) em UTF-8 = 0xC3 0xA1 -> Latin-1 = 'A¡'
      'ã' em UTF-8 = 0xC3 0xA3 -> Latin-1 = 'A£'
      'e' em UTF-8 = 0xC3 0xA9 -> Latin-1 = 'A©'
      'c,' em UTF-8 = 0xC3 0xA7 -> Latin-1 = 'A§'
    Evita falsos positivos com textos corretos em português (ex: 'NÃO', 'SERTÃO').
    """
    if not texto:
        return False
    # Padrões reais de mojibake UTF-8->Latin-1: 'A' seguido de char com ord >= 0xA0 (160)
    # Estes são os bytes continuation do UTF-8 mapeados para Latin-1
    mojibake_pairs = [
        "A¡",  # a (a agudo)
        "A£",  # a~ (a til)
        "A§",  # c, (cedilha)
        "A©",  # e' (e agudo)
        "Aª",  # e^ (e circunflexo)
        "A­",  # i' (i agudo)
        "A³",  # o' (o agudo)
        "Aµ",  # o~ (o til)
        "Aº",  # u' (u agudo)
        "A¼",  # u~ (u crase com acento)
        "A¼",  # u' (u agudo caso alternativo)
        "A¿",  # ? caractere especial
        "A´",  # o^ (o circunflexo)
        "A¶",  # o (o diaeresis)
        "A¸",  # o~ alternativo
        "A¹",  # u grave
        "A»",  # u circunflexo
        "A¾",  # thorn
        "A°",  # a ring
        "A²",  # o grave
        "A´",  # o acute
        "A®",  # i diaeresis
        "A¬",  # i grave
        "A¯",  # i macron
        "A±",  # n tilde
        "A«",  # e umlaut
        "A¨",  # e grave
        "A¦",  # ae
        "A¥",  # a tilde alternativo
        "A¢",  # cent / variante
        "A¤",  # currency / variante
        "A¿",  # inverted question mark
        "A¾",  # 3/4
        "A½",  # 1/2
        "A¼",  # 1/4
        "A·",  # middle dot
        "A¶",  # pilcrow
        "Aµ",  # micro / o tilde
        "A´",  # acute accent / o circ
        "A³",  # superscript 3 / o acute
        "A²",  # superscript 2 / o grave
        "A±",  # plus-minus / n tilde
        "A°",  # degree sign / a ring
        "A¯",  # macron / i macron
        "A®",  # registered / i diaeresis
        "A­",  # soft hyphen / i acute
        "A¬",  # not sign / i grave
        "A«",  # left guillemot / e umlaut
        "Aª",  # feminine ordinal / e circ
        "A©",  # copyright / e acute
        "A¨",  # diaeresis / e grave
        "A§",  # section / cedilha
        "A¦",  # broken bar / ae
        "A¥",  # yen / a tilde
        "A¤",  # currency / a umlaut
        "A£",  # pound / a tilde
        "A¢",  # cent / a acute
        "A¡",  # inverted ! / a acute
        "â€“", "â€‘", "â€œ", "â€",  # aspas e travessoes unicode
    ]
    return any(p in texto for p in mojibake_pairs)

def tentar_reparar_mojibake(texto: str) -> str:
    """
    Tenta reparar mojibake decodificando como Latin-1 e re-interpretando como UTF-8.
    Exemplo: "MÃ¡rcia" → encode('latin-1') → bytes UTF-8 → decode('utf-8') → "Márcia"
    """
    try:
        reparado = texto.encode("latin-1").decode("utf-8")
        return unicodedata.normalize("NFC", reparado)
    except (UnicodeDecodeError, UnicodeEncodeError):
        return texto

def normalizar_id3_arquivo(caminho: str, dry_run: bool = False) -> dict:
    """
    Normaliza as tags ID3 de um arquivo MP3 para compatibilidade com ZaraRadio.
    
    Returns:
        dict com 'status' (ok, alterado, erro, ignorado), 'antes', 'depois'
    """
    try:
        from mutagen.id3 import ID3, TIT2, TPE1, TALB, ID3NoHeaderError
        from mutagen.id3 import Encoding
    except ImportError:
        logger.error("mutagen não está instalado. Execute: pip install mutagen")
        return {"status": "erro", "motivo": "mutagen ausente"}

    try:
        try:
            tags = ID3(caminho)
        except ID3NoHeaderError:
            return {"status": "ignorado", "motivo": "sem tags ID3"}

        campos = {
            "TIT2": (TIT2, "título"),
            "TPE1": (TPE1, "artista"),
            "TALB": (TALB, "álbum"),
        }

        antes = {}
        depois = {}
        alterado = False

        for frame_id, (FrameClass, nome) in campos.items():
            frame = tags.get(frame_id)
            if not frame:
                continue
            valor_original = str(frame)
            antes[nome] = valor_original

            # Detecta e repara mojibake
            if tem_mojibake(valor_original):
                valor_corrigido = tentar_reparar_mojibake(valor_original)
                logger.info(f"  Mojibake detectado em {nome}: '{valor_original}' -> '{valor_corrigido}'")

            else:
                valor_corrigido = normalizar_tag_texto(valor_original)

            depois[nome] = valor_corrigido

            if valor_original != valor_corrigido:
                alterado = True
                if not dry_run:
                    # Encoding.LATIN1 = 0x00, compatível com ID3v2.3 + ZaraRadio
                    tags[frame_id] = FrameClass(encoding=Encoding.LATIN1, text=[valor_corrigido])

        if alterado:
            if not dry_run:
                # Salva forçando ID3v2.3 (mais compatível com ZaraRadio)
                tags.save(caminho, v2_version=3)
            logger.info(f"{'[DRY-RUN] ' if dry_run else ''}Corrigido: {os.path.basename(caminho)}")
            return {"status": "alterado", "antes": antes, "depois": depois}
        else:
            return {"status": "ok", "antes": antes, "depois": depois}

    except Exception as e:
        logger.warning(f"Erro ao processar '{caminho}': {e}")
        return {"status": "erro", "motivo": str(e)}

def processar_acervo(pasta: str, dry_run: bool = False) -> dict:
    """Varre recursivamente a pasta e normaliza todos os arquivos MP3."""
    if not os.path.isdir(pasta):
        logger.error(f"Pasta não encontrada: {pasta}")
        return {"erro": f"Pasta não encontrada: {pasta}"}

    os.makedirs("logs", exist_ok=True)

    total = 0
    alterados = 0
    erros = 0
    ignorados = 0

    logger.info(f"{'[DRY-RUN] ' if dry_run else ''}Varrendo: {pasta}")

    for root, _, files in os.walk(pasta):
        for fname in files:
            ext = Path(fname).suffix.lower()
            if ext not in AUDIO_EXTENSIONS:
                continue
            caminho_completo = os.path.join(root, fname)
            total += 1
            resultado = normalizar_id3_arquivo(caminho_completo, dry_run=dry_run)
            status = resultado.get("status")
            if status == "alterado":
                alterados += 1
            elif status == "erro":
                erros += 1
            elif status == "ignorado":
                ignorados += 1

    logger.info(
        f"\n{'='*50}\n"
        f"Resultado {'(DRY-RUN) ' if dry_run else ''}da normalização ID3:\n"
        f"  Total processados: {total}\n"
        f"  Corrigidos:        {alterados}\n"
        f"  Sem alteração:     {total - alterados - erros - ignorados}\n"
        f"  Sem tags ID3:      {ignorados}\n"
        f"  Erros:             {erros}\n"
        f"{'='*50}"
    )
    return {"total": total, "alterados": alterados, "erros": erros, "ignorados": ignorados}

def main():
    parser = argparse.ArgumentParser(
        description="Normaliza encoding de tags ID3 para compatibilidade com ZaraRadio (cp1252/Latin-1)."
    )
    parser.add_argument(
        "--pasta",
        default=None,
        help="Pasta raiz do acervo de músicas. Padrão: lido do settings.json."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Modo leitura: mostra o que seria alterado sem modificar arquivos."
    )
    args = parser.parse_args()

    pasta = args.pasta or detectar_pasta_musicas()
    processar_acervo(pasta, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
