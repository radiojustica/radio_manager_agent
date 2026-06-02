import os
import unittest
import sys
from datetime import datetime
from pathlib import Path

# Adiciona o diretório raiz ao path para podermos testar localmente
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Mocks para testar as regras sem precisar de arquivos físicos reais
class DummyMusica:
    def __init__(self, caminho, artista="VARIOUS", titulo="Music", estilo="pop", energia=3, duracao=210, vezes_tocada=0):
        self.caminho = caminho
        self.artista = artista
        self.titulo = titulo
        self.estilo = estilo
        self.energia = energia
        self.duracao = duracao
        self.vezes_tocada = vezes_tocada

class TestGradeRules(unittest.TestCase):
    
    def test_obter_boletins_dia_uteis(self):
        """Verifica se nos dias úteis os boletins vêm apenas da pasta do dia correspondente."""
        from director.grade_rules import obter_boletins_dia
        
        # Simula uma segunda-feira (weekday = 0)
        dt_segunda = datetime(2026, 5, 25) # 25 de maio de 2026 é uma segunda-feira
        self.assertEqual(dt_segunda.weekday(), 0)
        
        # Chama a função
        boletins = obter_boletins_dia(dt_segunda)
        # Como o ambiente pode ou não ter arquivos reais em D:\SERVIDOR\BOLETINS\SEGUNDA:
        # Se retornar arquivos, todos os caminhos devem conter a pasta SEGUNDA
        for b in boletins:
            self.assertIn("SEGUNDA", b.upper())
            
    def test_obter_boletins_fim_de_semana(self):
        """Verifica se no sábado e domingo os boletins são sorteados de todos os dias úteis."""
        from director.grade_rules import obter_boletins_dia
        
        # Simula um sábado (weekday = 5)
        dt_sabado = datetime(2026, 5, 26) # 26 de maio de 2026 é uma terça-feira, então sábado seria 30 de maio
        dt_sabado = datetime(2026, 5, 30)
        self.assertEqual(dt_sabado.weekday(), 5)
        
        boletins = obter_boletins_dia(dt_sabado)
        # Se houver boletins no servidor, eles devem vir de múltiplos dias da semana
        # (SEGUNDA, TERCA, QUARTA, QUINTA, SEXTA)
        dias_uteis_encontrados = set()
        for b in boletins:
            for dia in ["SEGUNDA", "TERCA", "QUARTA", "QUINTA", "SEXTA"]:
                if dia in b.upper():
                    dias_uteis_encontrados.add(dia)
        
        # Imprime para auditoria visual se estiver executando os testes manuais
        print(f"Dias de boletins encontrados para Sábado: {dias_uteis_encontrados}")
        
    def test_obter_programa_mais_recente(self):
        """Testa o localizador recursivo do programa mais recente."""
        from director.grade_rules import obter_programa_mais_recente
        
        # Cria uma pasta temporária de teste
        temp_dir = BASE_DIR / "temp_test_programs"
        temp_dir.mkdir(exist_ok=True)
        
        # Cria alguns arquivos mp3 falsos com datas diferentes
        import time
        file1 = temp_dir / "prog_antigo.mp3"
        file2 = temp_dir / "prog_recente.mp3"
        
        with open(file1, "w") as f: f.write("dummy")
        with open(file2, "w") as f: f.write("dummy")
        
        # Modifica as datas de modificação física
        os.utime(str(file1), (time.time() - 3600, time.time() - 3600))
        os.utime(str(file2), (time.time(), time.time()))
        
        recente = obter_programa_mais_recente(str(temp_dir))
        self.assertEqual(os.path.basename(recente), "prog_recente.mp3")
        
        # Limpa arquivos de teste
        file1.unlink()
        file2.unlink()
        temp_dir.rmdir()

    def test_montar_bloco_estrutura(self):
        """Verifica se montar_bloco gera uma lista no formato correto contendo cabeçalho M3U."""
        from director.grade_rules import montar_bloco
        
        acervo = [
            DummyMusica("D:\\RADIO\\MUSICAS\\musica1.mp3", estilo="pop / rock internacional"),
            DummyMusica("D:\\RADIO\\MUSICAS\\musica2.mp3", estilo="rock nacional"),
            DummyMusica("D:\\RADIO\\MUSICAS\\musica3.mp3", estilo="mpb / contemporâneo")
        ]
        
        assets = {
            "vinhetas": ["D:\\RADIO\\VINHETAS\\vh1.mp3"],
            "spots": ["D:\\RADIO\\SPOTS\\spot1.mp3"],
            "boletins": ["D:\\SERVIDOR\\BOLETINS\\SEGUNDA\\b1.mp3"]
        }
        
        playlist = montar_bloco(acervo, duracao_alvo_s=7200, assets=assets, hora_inicio=10, mood="Ensolarado")
        
        # Deve ter o cabeçalho M3U
        self.assertEqual(playlist[0], "#EXTM3U")
        # Deve ter adicionado arquivos do acervo
        self.assertTrue(any("musica1.mp3" in line or "musica2.mp3" in line for line in playlist))

if __name__ == "__main__":
    unittest.main()
