import requests
import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger("OmniCore.StreamingStats")

class StreamingStats:
    def __init__(self, config: dict):
        self.enabled = config.get("enabled", False)
        self.server_type = config.get("server_type", "icecast") # icecast ou shoutcast
        self.url = config.get("url", "http://localhost:8000/status-json.xsl")
        self.mount = config.get("mount", "/stream")
        
    def get_listeners(self) -> int:
        if not self.enabled:
            return 0
            
        try:
            response = requests.get(self.url, timeout=3)
            if response.status_code != 200:
                return 0
                
            if self.server_type == "icecast":
                # Icecast JSON (status-json.xsl)
                try:
                    data = response.json()
                    sources = data.get("icestats", {}).get("source", [])
                    if isinstance(sources, dict):
                        sources = [sources]
                        
                    for source in sources:
                        if source.get("listenurl", "").endswith(self.mount):
                            return int(source.get("listeners", 0))
                except Exception as e:
                    logger.debug(f"Icecast parse error (JSON): {e}")
                    
            elif self.server_type == "shoutcast":
                # Shoutcast XML (stats?sid=1)
                try:
                    root = ET.fromstring(response.text)
                    current_listeners = root.find("CURRENTLISTENERS")
                    if current_listeners is not None:
                        return int(current_listeners.text)
                except Exception as e:
                    logger.debug(f"Shoutcast parse error: {e}")
                    
        except Exception as e:
            logger.debug(f"Erro ao buscar stats de streaming: {e}")
            
        return 0

# A instância será criada no router


