"""
Utilitários de manipulação segura de caminhos.
Previne path traversal validando que o caminho resolvido
permanece dentro do diretório base permitido.
"""
from pathlib import Path


def safe_path(base_dir: Path | str, user_input: str) -> Path:
    """
    Constrói um caminho seguro dentro de base_dir.
    Lança ValueError se user_input tentar escapar do diretório base.

    Uso:
        path = safe_path(settings["grade"]["pasta_musicas"], filename)
    """
    base = Path(base_dir).resolve()
    resolved = (base / user_input).resolve()
    if not str(resolved).startswith(str(base)):
        raise ValueError(f"Path traversal bloqueado: '{user_input}' escapa de '{base}'")
    return resolved


def safe_join(*parts: str | Path) -> Path:
    """
    Junta partes de caminho e resolve o resultado.
    Não valida contra um base_dir — use safe_path quando houver input externo.
    """
    return Path(*parts).resolve()
