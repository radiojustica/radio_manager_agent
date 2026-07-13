import os
import sys
import unittest
from pathlib import Path
from datetime import datetime

# Adiciona o diretório raiz ao path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.compliance_validator import ComplianceValidator
from director.grade_rules import montar_bloco

class DummyMusica:
    def __init__(self, caminho, artista="ARTISTA TESTE", titulo="Musica Teste", estilo="pop", energia=3, duracao=210, vezes_tocada=0):
        self.caminho = caminho
        self.artista = artista
        self.titulo = titulo
        self.estilo = estilo
        self.energia = energia
        self.duracao = duracao
        self.vezes_tocada = vezes_tocada

class TestAssetCollisions(unittest.TestCase):
    def setUp(self):
        self.validator = ComplianceValidator()
        self.temp_m3u = BASE_DIR / "temp_test_playlist.m3u"

    def tearDown(self):
        if self.temp_m3u.exists():
            self.temp_m3u.unlink()

    def test_compliance_validator_rejects_consecutive_spots(self):
        """Verifica se o revisor de conformidade detecta e reprova dois spots consecutivos."""
        linhas = [
            "#EXTM3U",
            r"D:\RADIO\MUSICAS\musica1.mp3",
            r"D:\RADIO\SPOTS\spot1.mp3",
            r"D:\RADIO\SPOTS\spot2.mp3",
            r"D:\RADIO\MUSICAS\musica2.mp3",
        ]
        with open(self.temp_m3u, "w", encoding="cp1252") as f:
            f.write("\n".join(linhas))
            
        violations = self.validator.validate_playlist(str(self.temp_m3u), hour=10)
        self.assertTrue(any("colisão consecutiva de assets: SPOT" in v for v in violations), f"Violations: {violations}")

    def test_compliance_validator_rejects_consecutive_vinhetas(self):
        """Verifica se o revisor de conformidade detecta e reprova duas vinhetas consecutivas."""
        linhas = [
            "#EXTM3U",
            r"D:\RADIO\MUSICAS\musica1.mp3",
            r"D:\RADIO\VINHETAS\vht_institucional.mp3",
            r"D:\RADIO\VINHETAS\vht_passagem.mp3",
            r"D:\RADIO\MUSICAS\musica2.mp3",
        ]
        with open(self.temp_m3u, "w", encoding="cp1252") as f:
            f.write("\n".join(linhas))
            
        violations = self.validator.validate_playlist(str(self.temp_m3u), hour=10)
        self.assertTrue(any("colisão consecutiva de assets: VINHETA" in v for v in violations), f"Violations: {violations}")

    def test_compliance_validator_rejects_consecutive_boletins(self):
        """Verifica se o revisor de conformidade detecta e reprova dois boletins consecutivos."""
        linhas = [
            "#EXTM3U",
            r"D:\RADIO\MUSICAS\musica1.mp3",
            r"D:\SERVIDOR\BOLETINS\boletim1.mp3",
            r"D:\SERVIDOR\BOLETINS\boletim2.mp3",
            r"D:\RADIO\MUSICAS\musica2.mp3",
        ]
        with open(self.temp_m3u, "w", encoding="cp1252") as f:
            f.write("\n".join(linhas))
            
        violations = self.validator.validate_playlist(str(self.temp_m3u), hour=10)
        self.assertTrue(any("colisão consecutiva de assets: BOLETIM" in v for v in violations), f"Violations: {violations}")

    def test_grade_rules_prevents_consecutive_assets_on_generation(self):
        """Verifica se o motor de regras previne a colisão mesmo com boletim ausente."""
        acervo = [
            DummyMusica(r"D:\RADIO\MUSICAS\m1.mp3", estilo="pop rock"),
            DummyMusica(r"D:\RADIO\MUSICAS\m2.mp3", estilo="pop rock"),
            DummyMusica(r"D:\RADIO\MUSICAS\m3.mp3", estilo="pop rock"),
            DummyMusica(r"D:\RADIO\MUSICAS\m4.mp3", estilo="pop rock"),
        ]
        
        # Simulando um cenário de assets onde o boletim está vazio (sem arquivos no disco)
        assets = {
            "vinhetas": [r"D:\RADIO\VINHETAS\vht1.mp3"],
            "spots": [r"D:\RADIO\SPOTS\spot1.mp3"],
            "boletins": []  # Boletim indisponível!
        }
        
        # O evento agendado de loop a cada 30min tem a estrutura ["SPOT", "BOLETIM", "SPOT"]
        # Como o boletim está vazio, o motor deve omitir o segundo spot para evitar ["SPOT", "SPOT"]
        playlist_gerada = montar_bloco(
            acervo=acervo,
            duracao_alvo_s=3600,
            assets=assets,
            hora_inicio=10
        )
        
        # Grava a playlist gerada no arquivo temporário para validar com o ComplianceValidator
        with open(self.temp_m3u, "w", encoding="cp1252") as f:
            f.write("\n".join(playlist_gerada))
            
        # O ComplianceValidator não deve encontrar nenhuma violação consecutiva
        violations = self.validator.validate_playlist(str(self.temp_m3u), hour=10)
        
        # Filtra violações consecutivas
        consecutive_violations = [v for v in violations if "colisão consecutiva" in v]
        self.assertEqual(consecutive_violations, [], f"Gerou colisão de assets: {consecutive_violations}\nPlaylist: {playlist_gerada}")

if __name__ == "__main__":
    unittest.main()
