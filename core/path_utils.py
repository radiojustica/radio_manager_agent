from pathlib import Path
import os

def safe_path(base_dir: Path, user_input: str) -> Path:
    """
    Garante que um caminho construído a partir de entrada do usuário
    não faça escape (Path Traversal) do diretório base definido.
    """
    resolved_base = base_dir.resolve()
    resolved_user = (resolved_base / user_input).resolve()
    
    # Em Windows, comparar strings de caminhos de forma case-insensitive
    if not str(resolved_user).lower().startswith(str(resolved_base).lower() + os.sep.lower()) and str(resolved_user).lower() != str(resolved_base).lower():
        raise ValueError(f"Path traversal detectado: {user_input}")
    
    return resolved_user
