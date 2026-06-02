import os
import sys
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.bulletin_sync import BulletinSync

def test_parse_bulletin_info_valid():
    syncer = BulletinSync(source_dir="mock_src", target_dir="mock_tgt")
    
    # Padrão boletim: (\d{2})_(\d{2})_(\d{4})_B(\d+)
    valid_cases = [
        ("18_05_2026_B1.mp3", "18_05_2026_B1.mp3", 1, datetime(2026, 5, 18)),
        ("02_06_2026_B2.mp3", "02_06_2026_B2.mp3", 2, datetime(2026, 6, 2)),
    ]
    
    for filename, expected_name, expected_b_num, expected_date in valid_cases:
        info = syncer.parse_bulletin_info(filename)
        assert info is not None, f"Falhou ao reconhecer boletim válido: {filename}"
        assert info["filename"] == expected_name
        assert info["b_num"] == expected_b_num
        assert info["date"] == expected_date

def test_parse_bulletin_info_invalid():
    syncer = BulletinSync(source_dir="mock_src", target_dir="mock_tgt")
    
    # Casos a ignorar
    invalid_cases = [
        "18_05_2026.mp3",  # Sem número de boletim
        "18_05_26_B1.mp3",  # Ano com 2 dígitos
        "BOLETIM_OFF_18_05_2026_B1.mp3",  # Contém OFF
        "18_05_2026_B1_GRAVAÇÃO.mp3",  # Contém GRAVAÇÃO
        "18_05_2026_B1_GRAVACAO.mp3",  # Contém GRAVACAO
        "18_05_2026_B1_BRUTO.mp3",  # Contém BRUTO
        "18_05_2026_B1_PILOTO.mp3",  # Contém PILOTO
        "18_05_2026_B1_LEO.mp3",  # Contém LEO
        "18_05_2026_B1_LIV.mp3",  # Contém LIV
        "18_05_2026_B1_THI.mp3",  # Contém THI
        "18_05_2026_B1_LET.mp3",  # Contém LET
        "18_05_2026_B1_GRAV.mp3",  # Contém GRAV
        "PTT-20260602_18_05_2026_B1.mp3",  # Contém PTT-
        "18_05_2026_B1-WA0001.mp3",  # Contém -WA
        "AUD-20260602_18_05_2026_B1.mp3",  # Contém AUD-
    ]
    
    for filename in invalid_cases:
        info = syncer.parse_bulletin_info(filename)
        assert info is None, f"Deveria ter ignorado boletim inválido: {filename}"
