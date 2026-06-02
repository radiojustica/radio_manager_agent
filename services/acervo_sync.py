import os
import re
from pathlib import Path
from typing import List, Tuple

from core.database import SessionLocal
from core.models import Musica

AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a'}

def _parse_filename(file_path: Path) -> Tuple[str, str]:
    """Tentativa simples de extrair artista e título a partir do nome do arquivo.
    Espera que o arquivo siga o padrão "Artista - Título.ext".
    Se o padrão não combinar, usa o nome do arquivo como título e deixa artista vazio.
    """
    name = file_path.stem
    # Busca padrão "Artista - Título"
    match = re.match(r"(?P<artist>.+?)\s*-\s*(?P<title>.+)", name)
    if match:
        return match.group('artist').strip(), match.group('title').strip()
    return "", name.strip()

def sync_acervo(musica_dir: str = None) -> dict:
    """Escaneia recursivamente a pasta de músicas e popula/atualiza a tabela Musica.
    Args:
        musica_dir: pasta onde estão as músicas. Se ``None`` lê de ``settings.json``.
    Returns:
        dict com contagem de arquivos encontrados, inseridos, atualizados e erros.
    """
    # Carrega pasta de músicas do settings.json caso não seja passado explicitamente
    if not musica_dir:
        try:
            import json
            settings_path = os.path.join('config', 'settings.json')
            with open(settings_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            musica_dir = cfg.get('grade', {}).get('pasta_musicas')
        except Exception:
            return {"error": "Não foi possível obter pasta_musicas das configurações"}

    if not musica_dir or not os.path.isdir(musica_dir):
        return {"error": f"Pasta de músicas não encontrada: {musica_dir}"}

    db = SessionLocal()
    inserted = 0
    updated = 0
    errors: List[str] = []

    try:
        for root, _, files in os.walk(musica_dir):
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in AUDIO_EXTENSIONS:
                    continue
                full_path = os.path.abspath(os.path.join(root, fname))
                try:
                    artist, title = _parse_filename(Path(full_path))
                    
                    # Determina o tema especial com base na pasta física (Sazonalidade Robusta)
                    lower_path = full_path.lower()
                    tema = None
                    if "especial_natal" in lower_path:
                        tema = "natal"
                    elif "especial_junho" in lower_path:
                        tema = "junho"

                    # Busca registro existente
                    existing = db.query(Musica).filter(Musica.caminho == full_path).first()
                    if existing:
                        # Atualiza campos básicos caso estejam vazios
                        changed = False
                        if not existing.artista and artist:
                            existing.artista = artist
                            changed = True
                        if not existing.titulo and title:
                            existing.titulo = title
                            changed = True
                        # Atualiza tema_especial se estiver diferente ou vazio
                        if existing.tema_especial != tema:
                            existing.tema_especial = tema
                            changed = True
                        if changed:
                            db.add(existing)
                            updated += 1
                    else:
                        m = Musica(
                            caminho=full_path,
                            artista=artist or "VARIOUS",
                            titulo=title,
                            estilo="outros",
                            tema_especial=tema,
                        )
                        db.add(m)
                        inserted += 1
                except Exception as e:
                    errors.append(f"Erro ao processar {full_path}: {e}")
        db.commit()
    finally:
        db.close()

    return {
        "found": inserted + updated,
        "inserted": inserted,
        "updated": updated,
        "errors": errors,
    }
