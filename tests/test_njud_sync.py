import os
import sys
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.njud_sync import NjudSync

def test_parse_njud_info_valid():
    syncer = NjudSync(source_dir="mock_src", target_dir="mock_tgt")
    
    # Lista de arquivos que devem ser considerados válidos
    valid_cases = [
        ("NJUD 1792 08-01.mp3", "NJUD 1792 08-01.mp3"),
        ("NJUD 1809 02-02.mp3", "NJUD 1809 02-02.mp3"),
        ("NJUD 1759 - 03 11.mp3", "NJUD 1759 - 03 11.mp3"),
        ("njud 1826 02-03.mp3", "njud 1826 02-03.mp3"),
        ("NJUD 1821 23-02.mp3", "NJUD 1821 23-02.mp3"),
    ]
    
    for filename, expected_name in valid_cases:
        filepath = f"/some/path/{filename}"
        with patch("os.path.getmtime") as mock_mtime:
            mock_mtime.return_value = 1772345678.0  # Qualquer timestamp fixo
            info = syncer.parse_njud_info(filepath)
            assert info is not None, f"Falhou ao reconhecer arquivo válido: {filename}"
            assert info["filename"] == expected_name
            assert info["day_name"] in ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA", "SABADO", "DOMINGO"]

def test_parse_njud_info_invalid():
    syncer = NjudSync(source_dir="mock_src", target_dir="mock_tgt")
    
    # Lista de arquivos que devem ser ignorados (OFFs, brutas, sem data, etc)
    invalid_cases = [
        "NJUD 1823.mp3",  # Sem data
        "NJUD 1826 NOTAS.mp3",  # Notas
        "NJUD 1832 - LOCUÇÃO.mp3",  # Locução (contém LOC)
        "NJUD 1779 - APRESENTADOR.mp3",  # Contém APRESENTA
        "NJUD 1834 - APRESENTAÇÃO.mp3",  # Contém APRESENTA
        "OFF 01 02 03.mp3",  # Contém OFF
        "NJUD 1809 02-02 OFF.mp3",  # Contém OFF
        "NJUD 1853 LOC.mp3",  # Contém LOC
        "NJUD 01-12.mp3",  # Sem número
        "NJUD 1826.wav",  # Extensão errada
        "MODELO ROTEIRO NJUD.gdoc",  # Extensão errada
        "NJUD 1881 26-05 LEO.mp3",  # Contém LEO
        "NJUD 1881 26-05 LIV.mp3",  # Contém LIV
        "NJUD 1881 26-05 THI.mp3",  # Contém THI
        "NJUD 1881 26-05 LET.mp3",  # Contém LET
        "NJUD 1881 26-05 GRAV.mp3",  # Contém GRAV
        "NJUD 1881 26-05 PTT-2026.mp3",  # Contém PTT-
        "NJUD 1881 26-05-WA0001.mp3",  # Contém -WA
        "NJUD 1881 26-05 AUD-2026.mp3",  # Contém AUD-
    ]
    
    for filename in invalid_cases:
        filepath = f"/some/path/{filename}"
        info = syncer.parse_njud_info(filepath)
        assert info is None, f"Deveria ter ignorado arquivo inválido: {filename}"

@patch("os.path.exists")
@patch("os.walk")
@patch("shutil.copy2")
@patch("os.listdir")
@patch("os.remove")
@patch("os.path.getmtime")
def test_sync_operation(mock_getmtime, mock_remove, mock_listdir, mock_copy, mock_walk, mock_exists, tmp_path):
    # Setup
    def side_effect_exists(path):
        if path == "mock_src":
            return True
        return False
    mock_exists.side_effect = side_effect_exists
    
    # Simulamos arquivos na pasta do Drive
    # Terça-feira (weekday=1), Quinta-feira (weekday=3)
    # NJUD 1809 02-02 -> mtime correspondente a uma Terça
    # NJUD 1812 05-02 -> mtime correspondente a uma Quinta
    mock_walk.return_value = [
        ("mock_src", [], ["NJUD 1809 02-02.mp3", "NJUD 1812 05-02.mp3", "NJUD 1809 02-02 OFF.mp3", "NJUD 1823.mp3"])
    ]
    
    # Mockando getmtime para retornar datas específicas
    # 2026-02-03 (Terça) e 2026-02-05 (Quinta)
    def side_effect_mtime(path):
        if "NJUD 1809 02-02.mp3" in path:
            return datetime(2026, 2, 3, 10, 0, 0).timestamp()
        elif "NJUD 1812 05-02.mp3" in path:
            return datetime(2026, 2, 5, 10, 0, 0).timestamp()
        return datetime(2026, 2, 1, 10, 0, 0).timestamp()
        
    mock_getmtime.side_effect = side_effect_mtime
    mock_listdir.return_value = []
    
    syncer = NjudSync(source_dir="mock_src", target_dir="mock_tgt")
    
    res = syncer.sync()
    
    assert res["success"] is True
    assert res["updated"] == 2
    assert res["total_matched"] == 2
    assert res["total_scanned"] == 4
    
    # Verifica que copiou para TERCA e QUINTA
    assert mock_copy.call_count == 2
