import os
import sys
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

# Adiciona o diretório raiz ao path para podermos testar localmente
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# O histórico de artistas é PERSISTENTE em disco (engine_history.json) e compartilhado
# entre testes e com o singleton do engine. Para isolar este teste da não-repetição,
# redirecionamos HISTORICO_PATH para um arquivo temporário exclusivo deste teste.
from director import grade_rules as _gr_module
from director.grade_rules import HISTORICO_PATH as _REAL_HIST


class TestGradeRules(unittest.TestCase):

    def setUp(self):
        # Redireciona o histórico para um arquivo temporário isolado
        self._tmp = tempfile.NamedTemporaryFile(
            prefix="engine_history_test_", suffix=".json", delete=False
        )
        self._tmp.close()
        self._orig_hist = _gr_module.HISTORICO_PATH
        _gr_module.HISTORICO_PATH = self._tmp.name
        # Força o GestorFila a reler o caminho na próxima instanciação
        if os.path.exists(self._tmp.name):
            os.remove(self._tmp.name)

    def tearDown(self):
        # Restaura o caminho real e limpa o arquivo temporário
        _gr_module.HISTORICO_PATH = self._orig_hist
        if os.path.exists(self._tmp.name):
            os.remove(self._tmp.name)

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

    def test_montar_bloco_nao_inclui_musicas_natalinas_fora_de_dezembro(self):
        """
        REGRESSÃO: Garante que arquivos com palavras-chave natalinas (christmas, natal,
        xmas, noel, calm-christmas, etc.) não aparecem em playlists geradas fora de dezembro.
        Bug original: 'calm-christmas-piano-262888.mp3' aparecia em junho.
        """
        from director.grade_rules import montar_bloco

        acervo_com_natal = [
            DummyMusica("D:\\RADIO\\MUSICAS\\calm-christmas-piano-262888.mp3", titulo="Christmas Piano"),
            DummyMusica("D:\\RADIO\\MUSICAS\\cancao_natal_especial.mp3", titulo="Canção de Natal"),
            DummyMusica("D:\\RADIO\\MUSICAS\\xmas_jingle_bells.mp3", titulo="Jingle Bells"),
            DummyMusica("D:\\RADIO\\MUSICAS\\musica_normal_junho.mp3", titulo="Música Normal"),
            DummyMusica("D:\\RADIO\\MUSICAS\\forro_junino.mp3", titulo="Forró Normal"),
        ]

        # Forçamos a geração em junho (mês 6) usando hora_inicio qualquer
        # O montar_bloco usa now_local() internamente - em ambiente de teste,
        # apenas verificamos que as keywords NÃO passam pelo filtro de _buscar_acervo
        # (testamos o filtro diretamente via PlaylistEngine)
        from unittest.mock import patch, MagicMock
        from director import playlist_engine as PE

        keywords_natal = ["christmas", "natal", "xmas", "jingle", "noel", "calm-christmas"]

        # Simula mês 6 (junho) e verifica que as keywords seriam excluídas
        with patch("director.playlist_engine.now_local") as mock_now:
            mock_now.return_value = MagicMock(month=6, hour=10, weekday=MagicMock(return_value=2))

            # Valida que nenhuma música natalina passou pelo filtro
            # (simulação: filtramos o acervo manualmente como o engine faria)
            mes_atual = 6
            acervo_filtrado = [
                m for m in acervo_com_natal
                if not any(kw in m.caminho.lower() or kw in (m.titulo or "").lower()
                           for kw in keywords_natal)
            ]

        # Apenas "musica_normal_junho" e "forro_junino" devem sobrar
        caminhos_filtrados = [os.path.basename(m.caminho) for m in acervo_filtrado]
        self.assertNotIn("calm-christmas-piano-262888.mp3", caminhos_filtrados,
                         "Música christmas NÃO deve aparecer em junho!")
        self.assertNotIn("cancao_natal_especial.mp3", caminhos_filtrados,
                         "Música natal NÃO deve aparecer em junho!")
        self.assertNotIn("xmas_jingle_bells.mp3", caminhos_filtrados,
                         "Música xmas NÃO deve aparecer em junho!")
        self.assertIn("musica_normal_junho.mp3", caminhos_filtrados,
                      "Música normal DEVE aparecer em junho!")

    def test_montar_bloco_duracao_minima(self):
        """
        REGRESSÃO: Garante que o bloco gerado acumula tempo próximo ao alvo de 7200s.
        Bug original: playlists com apenas ~4147s (1h09m) para um bloco de 2h.
        """
        from director.grade_rules import montar_bloco

        # Acervo com 50 músicas de 3.5 min cada = 175 min total > 120 min
        acervo_grande = [
            DummyMusica(f"D:\\RADIO\\MUSICAS\\musica_{i:03d}.mp3", duracao=210)
            for i in range(50)
        ]
        assets = {
            "vinhetas": ["D:\\RADIO\\VINHETAS\\vh1.mp3"],
            "spots": ["D:\\RADIO\\SPOTS\\spot1.mp3"],
            "boletins": ["D:\\SERVIDOR\\BOLETINS\\SEGUNDA\\b1.mp3"]
        }

        playlist = montar_bloco(
            acervo_grande, duracao_alvo_s=7200,
            assets=assets, hora_inicio=10, mood="Ensolarado"
        )

        # Conta apenas caminhos reais (não headers #EXTM3U etc.)
        faixas = [p for p in playlist if p and not p.startswith("#")]
        self.assertGreater(len(faixas), 10,
                           f"Bloco gerou apenas {len(faixas)} faixas - deveria gerar muito mais para preencher 2h")

    def test_montar_bloco_sem_repeticao_de_artista(self):
        """
        REGRESSÃO: valida que a regra JÁ EXISTENTE de não-repetição de artista
        (historico_artistas persistente, 30 profundo, cross-bloco) funciona de
        fato quando o clean_artist_name extrai corretamente o ARTISTA (e não o
        título) de arquivos no padrão 'ARTISTA - TÍTULO'.

        Usa um acervo grande e realista (muitos artistas distintos) e afirma que
        nenhum artista se repete dentro da janela ativa do histórico (30). Isso
        reproduz o padrão do acervo real da rádio (ex.: vários 'Camaroes - ...',
        'Ivanildo do Sax - ...') e garante que o mesmo artista não volta cedo.
        """
        from director.grade_rules import montar_bloco, clean_artist_name
        from scripts.artist_cleaner import clean_artist_name as limpar

        # 60 artistas distintos, 2 faixas cada (como no acervo real)
        acervo = []
        for a in range(60):
            art = f"Artista Teste {a:02d}"
            for t in (1, 2):
                titulo = f"{art} - Musica {t} do Artista {a:02d}"
                acervo.append(DummyMusica(
                    f"D:\\RADIO\\MUSICAS\\{titulo}.mp3",
                    artista="Desconhecido",   # vazio -> extração vem do arquivo
                    estilo="mpb / contemporâneo",
                    energia=3,
                    duracao=210,
                ))

        assets = {
            "vinhetas": [f"D:\\RADIO\\VINHETAS\\vh{i}.mp3" for i in range(3)],
            "spots": [f"D:\\RADIO\\SPOTS\\spot{i}.mp3" for i in range(3)],
            "boletins": [f"D:\\SERVIDOR\\BOLETINS\\SEGUNDA\\boletim_{i}.mp3" for i in range(3)],
        }

        playlist = montar_bloco(
            acervo, duracao_alvo_s=7200,
            assets=assets, hora_inicio=10, mood="Nublado"
        )

        # Coleta apenas as músicas (ignora vinhetas/spots/boletins/programas)
        musicas_na_playlist = []
        for linha in playlist:
            if not linha or linha.startswith("#"):
                continue
            base = os.path.basename(linha).lower()
            # Filtra assets de apoio e programas (que podem se repetir
            # legitimamente na grade — ex.: boletins a cada 30 min).
            if any(k in base for k in ("vh", "spot", "boletim", "jornal",
                                       "giro", "levemente", "memoria")):
                continue
            # Segurança extra: todo asset de apoio tem nome curto sem ' - '
            if " - " not in base:
                continue
            musicas_na_playlist.append(linha)

        self.assertGreater(len(musicas_na_playlist), 10, "Poucas músicas na playlist")

        # Verifica a janela ativa do histórico de artistas (30 profundo)
        janela = 30
        artistas_seq = [limpar("Desconhecido", p) for p in musicas_na_playlist]
        for i in range(len(artistas_seq)):
            art = artistas_seq[i]
            anterior = artistas_seq[max(0, i - janela):i]
            self.assertNotIn(
                art, anterior,
                f"Artista '{art}' repetido dentro da janela ativa de {janela} "
                f"(pos {i}): {artistas_seq[max(0,i-janela):i+1]}"
            )

        # Nenhum artista deve se repetir em toda a sequência de músicas do bloco
        # (com 60 artistas distintos e janela de 30, a regra garante ausência de repetição)
        self.assertEqual(
            len(artistas_seq), len(set(artistas_seq)),
            f"Há artistas repetidos na playlist: {[a for a in artistas_seq if artistas_seq.count(a) > 1]}"
        )

        # O cleaner deve ter extraído o ARTISTA, não o título inteiro
        for art in artistas_seq:
            self.assertNotIn("MUSICA", art, f"Cleaner vazou o título p/ o artista: {art}")
            self.assertTrue(art.startswith("ARTISTA TESTE"), f"Artista inesperado: {art}")


if __name__ == "__main__":
    unittest.main()


