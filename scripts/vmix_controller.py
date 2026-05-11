import requests
import xml.etree.ElementTree as ET
import logging
from typing import Tuple, Optional


class VMixController:
    def __init__(self, ip: str = "172.16.217.226", port: int = 8088):
        self.base_url = f"http://{ip}:{port}/api"
        self.logger = logging.getLogger("RadioManagerAgent.VMix")
        self.last_active_input: Optional[str] = None
        self.connected = False

    def get_status(self) -> Optional[ET.Element]:
        """Fetches the current state of vMix via XML API."""
        try:
            response = requests.get(self.base_url, timeout=2)
            if response.status_code == 200:
                self.connected = True
                return ET.fromstring(response.text)
            self.logger.warning(f"vMix returned HTTP {response.status_code}")
            return None
        except requests.exceptions.ConnectionError:
            if self.connected:
                self.logger.warning(f"Connection lost with vMix at {self.base_url}")
                self.connected = False
            return None
        except requests.exceptions.Timeout:
            if self.connected:
                self.logger.warning(f"vMix request timed out at {self.base_url}")
                self.connected = False
            return None
        except ET.ParseError as e:
            self.logger.error(f"vMix: Failed to parse XML response — {e}")
            return None
        except Exception as e:
            self.logger.error(f"vMix: Unexpected error — {e}")
            return None

    def get_active_input_name(self) -> Optional[str]:
        """Returns the name of the input currently in Program (Active)."""
        root = self.get_status()
        if root is None:
            return None

        active_node = root.find("active")
        inputs_node = root.find("inputs")

        if active_node is None or inputs_node is None:
            self.logger.debug("vMix XML missing <active> or <inputs> element.")
            return None

        active_input_num = active_node.text
        for input_node in inputs_node.findall("input"):
            if input_node.get("number") == active_input_num:
                return input_node.get("title")

        return None

    def send_command(self, function: str, input_name: str = None) -> bool:
        """Sends a command to vMix via its Web API.

        Example: send_command("Cut", "ABERTURA")
        """
        params = {"Function": function}
        if input_name:
            params["Input"] = input_name

        try:
            response = requests.get(self.base_url, params=params, timeout=2)
            if response.status_code == 200:
                self.logger.info(f"vMix Command Sent: {function} (Input: {input_name})")
                return True
            self.logger.error(f"vMix Command Failed: HTTP {response.status_code}")
            return False
        except Exception as e:
            self.logger.error(f"vMix: Failed to send command — {e}")
            return False

    def is_session_live(
        self,
        trigger_keywords: list = None
    ) -> Tuple[bool, Optional[str]]:
        """Checks if any active input matches the live session keywords.

        Returns:
            (is_live: bool, active_title: str | None)
        """
        if trigger_keywords is None:
            trigger_keywords = ["SESSAO PLEN", "ABERTURA", "PLENARIO"]

        active_title = self.get_active_input_name()

        if active_title is None:
            return False, None

        upper_title = active_title.upper()

        # Log only when the active input changes
        if upper_title != self.last_active_input:
            self.logger.info(f"vMix Active Input: {active_title}")
            self.last_active_input = upper_title

        # Ignore standard vMix NDI output names to avoid false positives
        if "OUTPUT" in upper_title and "NDI" in upper_title:
            return False, active_title

        for kw in trigger_keywords:
            if kw.upper() in upper_title:
                return True, active_title

        return False, active_title


