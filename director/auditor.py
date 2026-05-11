"""
Programming Auditor — Omni Core V2
===================================
O "Vigia" técnico. Lê arquivos e logs para garantir o cumprimento das regras do Perfil.
"""

import os
import logging
from director.profile import PROFILE
from scripts.artist_cleaner import clean_artist_name

logger = logging.getLogger("OmniCore.Auditor")

class ProgrammingAuditor:
    def __init__(self):
        self.constraints = PROFILE["constraints"]

    def audit_file(self, file_path: str) -> list:
        """Verifica se um arquivo M3U cumpre as regras de rodízio."""
        violations = []
        if not os.path.exists(file_path):
            return [{"error": "Arquivo não encontrado"}]

        try:
            with open(file_path, "r", encoding="cp1252", errors="ignore") as f:
                # Filtra apenas o que é música (ignora vinhetas/spots/boletins)
                lines = [l.strip() for l in f if l.strip() and r"D:\RADIO\MUSICAS" in l.upper()]
            
            artist_window = self.constraints["artist_separation_count"]
            track_window = self.constraints["track_separation_count"]

            # Auditoria de Artista
            for i in range(len(lines)):
                # Olhamos para frente na janela definida
                window = lines[i : i + artist_window]
                if not window: break
                
                artistas = [clean_artist_name(None, path) for path in window]
                atual = artistas[0]
                
                if atual != "VARIOUS" and artistas.count(atual) > 1:
                    violations.append(f"Artista '{atual}' repete na janela de {artist_window} músicas.")
                    break # Registra apenas a primeira falha do arquivo para forçar regen
                    
        except Exception as e:
            logger.error(f"Erro na auditoria do arquivo {file_path}: {e}")
            violations.append(f"Erro técnico: {e}")

        return violations

    def audit_execution_log(self, log_path: str) -> list:
        """Verifica se o que FOI TOCADO (log real do ZaraRadio) respeitou as regras."""
        violations = []
        if not os.path.exists(log_path):
            return [{"error": f"Log não encontrado: {log_path}"}]

        try:
            # O log do ZaraRadio tem o formato: HH:MM:SS\t[ação]\t[caminho]
            # Ex: 10:15:33	início	D:\RADIO\MUSICAS\NACIONAL\Leny Andrade - Dez a Um.mp3
            played_tracks = []
            
            with open(log_path, "r", encoding="cp1252", errors="ignore") as f:
                for line in f:
                    parts = line.strip().split("\t")
                    if len(parts) >= 3 and parts[1].lower() == "início":
                        path = parts[2]
                        # Filtra apenas o que é música
                        if r"D:\RADIO\MUSICAS" in path.upper():
                            played_tracks.append(path)
            
            artist_window = self.constraints["artist_separation_count"]
            
            # Auditoria de Retrocesso (Verifica cada música contra as X anteriores)
            for i in range(len(played_tracks)):
                # Janela histórica de músicas tocadas antes desta
                start_idx = max(0, i - artist_window)
                history = played_tracks[start_idx : i]
                
                if not history: continue
                
                current_art = clean_artist_name(None, played_tracks[i])
                if current_art == "VARIOUS": continue
                
                # Extrai artistas do histórico
                history_artists = [clean_artist_name(None, p) for p in history]
                
                if current_art in history_artists:
                    # Acha a distância da última vez que tocou
                    distancia = history_artists[::-1].index(current_art) + 1
                    violations.append({
                        "artista": current_art,
                        "musica": os.path.basename(played_tracks[i]),
                        "distancia": distancia,
                        "regra": artist_window,
                        "msg": f"Artista '{current_art}' repetiu após apenas {distancia} músicas (Regra: {artist_window})."
                    })
                    
        except Exception as e:
            logger.error(f"Erro na auditoria do log {log_path}: {e}")
            violations.append({"error": str(e)})

        return violations


