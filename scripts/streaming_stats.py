import requests
import defusedxml.ElementTree as ET
import logging
import json
import os

logger = logging.getLogger("OmniCore.StreamingStats")

# Configuração carregada de settings.json — não hardcoded
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "settings.json")


def _load_streaming_config():
    """Carrega config de streaming de config/settings.json se disponível."""
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("streaming", {})
    except Exception:
        return {}


class StreamingStats:
    """Busca ouvintes reais do Icecast/Shoutcast via status-json.xsl ou stats XML."""

    def __init__(self, config: dict = None):
        cfg = config or _load_streaming_config()
        self.enabled = cfg.get("enabled", False)
        self.server_type = cfg.get("server_type", "icecast")
        self.url = cfg.get("url", "http://localhost:8000/status-json.xsl")
        self.mount = cfg.get("mount", "/stream")

    def get_listeners(self) -> int:
        """Retorna o número de ouvintes reais ou -1 se o streaming não está acessível."""
        if not self.enabled:
            return -1  # -1 significa 'não monitorado', não 'zero ouvintes'

        try:
            response = requests.get(self.url, timeout=3)
            if response.status_code != 200:
                logger.debug("StreamingStats: HTTP %d em %s", response.status_code, self.url)
                return -1

            if self.server_type == "icecast":
                try:
                    data = response.json()
                    sources = data.get("icestats", {}).get("source", [])
                    if isinstance(sources, dict):
                        sources = [sources]
                    for source in sources:
                        if source.get("listenurl", "").endswith(self.mount):
                            return int(source.get("listeners", 0))
                except (json.JSONDecodeError, ValueError) as e:
                    logger.debug("Icecast JSON parse error: %s", e)

            elif self.server_type == "shoutcast":
                try:
                    root = ET.fromstring(response.text)
                    current_listeners = root.find("CURRENTLISTeners")
                    if current_listeners is not None:
                        return int(current_listeners.text)
                except ET.ParseError as e:
                    logger.debug("Shoutcast XML parse error: %s", e)

        except requests.RequestException as e:
            logger.debug("Erro ao buscar stats de streaming: %s", e)

        return -1
