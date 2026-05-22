"""
Ponto único de carregamento de configuração.
Mescla settings.json com variáveis de ambiente do .env.
Uso: from core.config_loader import get_settings, get_secret
"""
import json
import os
import sys
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("OmniCore.ConfigLoader")

# Carrega .env uma única vez na importação do módulo
def _load_dotenv():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        logger.warning(f".env não encontrado em {env_path}. Usando apenas variáveis de ambiente do sistema.")
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

_load_dotenv()


def _resolve_env_placeholders(obj: Any) -> Any:
    """Substitui valores ${VAR} no settings.json pelas variáveis de ambiente."""
    if isinstance(obj, str):
        if obj.startswith("${") and obj.endswith("}"):
            var_name = obj[2:-1]
            value = os.environ.get(var_name, "")
            if not value:
                logger.warning(f"Variável de ambiente '{var_name}' não definida.")
            return value
        return obj
    if isinstance(obj, dict):
        return {k: _resolve_env_placeholders(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_env_placeholders(i) for i in obj]
    return obj


def _find_config_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "config" / "settings.json"


_settings_cache: dict | None = None


def get_settings() -> dict:
    """Retorna as configurações mescladas (settings.json + .env). Resultado em cache."""
    global _settings_cache
    if _settings_cache is not None:
        return _settings_cache

    config_path = _find_config_path()
    if not config_path.exists():
        logger.error(f"settings.json não encontrado em {config_path}. Usando configuração vazia.")
        _settings_cache = {}
        return _settings_cache

    try:
        with open(config_path, encoding="utf-8") as f:
            raw = json.load(f)
        _settings_cache = _resolve_env_placeholders(raw)
        logger.info(f"Configuração carregada de {config_path}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON inválido em settings.json: {e}")
        _settings_cache = {}
    except Exception as e:
        logger.error(f"Erro ao carregar settings.json: {e}")
        _settings_cache = {}

    return _settings_cache


def get_secret(key: str, default: str = "") -> str:
    """Lê um segredo diretamente das variáveis de ambiente."""
    value = os.environ.get(key, default)
    if not value:
        logger.warning(f"Segredo '{key}' não encontrado nas variáveis de ambiente.")
    return value


def reload_settings() -> dict:
    """Força recarga do settings.json do disco (hot-reload)."""
    global _settings_cache
    _settings_cache = None
    return get_settings()
