"""
Director Profile — Omni Core V2
================================
Define o perfil de direção musical da Rádio TJRN. 
Este arquivo é a única fonte de verdade para as regras de negócio.
"""

from datetime import datetime
from core.time_utils import now_local

PROFILE = {
    "name": "Direção Artística TJRN",
    "version": "2.1.0",
    "last_update": now_local().isoformat(),
    
    # 1. Regras de Rodízio (Fair Rotation)
    "constraints": {
        "artist_separation_count": 15,    # Reduzido de 80 para 15
        "track_separation_count": 80,    # Reduzido de 200 para 80
        "min_daily_rotation_goal": 0.90, # Meta: 90% do acervo deve girar antes de repetir
    },
    
    # 2. Quotas de Programação
    "quotas": {
        "regional_ratio": 1/8,           # 1 regional a cada 8 faixas
        "vinheta_ratio": 1/1,            # 1 vinheta a cada música
        "spot_ratio": 1/4,               # 1 spot a cada 4 músicas
        "boletim_ratio": 1/8,            # 1 boletim a cada 8 músicas
    },
    
    # 3. Definições de Energia (Dayparting)
    "dayparting": {
        "MADRUGADA": {"range": (0, 6),  "energies": [1, 2, 3]},
        "MANHA":     {"range": (6, 10), "energies": [4, 5]},
        "TARDE":     {"range": (10, 16), "energies": [3, 4]},
        "FIM_TARDE": {"range": (16, 20), "energies": [4, 5]},
        "NOITE":     {"range": (20, 24), "energies": [1, 2, 3]},
    },
    
    # 4. Comportamento em Falhas
    "policy": {
        "auto_redo_on_violation": True,  # Refaz a grade automaticamente se o auditor reprovar
        "max_retries": 3,                # Máximo de tentativas de regeneração
        "alert_on_failure": True,        # Notifica o Guardian se as regras forem quebradas
    }
}

def get_energies_for_hour(hour: int) -> list[int]:
    for period in PROFILE["dayparting"].values():
        start, end = period["range"]
        if start <= hour < end:
            return period["energies"]
    return [3] # Fallback


