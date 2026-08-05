import os
import glob
import logging
import random
from datetime import datetime, timedelta
from core.time_utils import now_local
from collections import Counter
from core.database import SessionLocal
from core.models import Musica
from director.profile import PROFILE

logger = logging.getLogger("OmniCore.MusicRecommender")

# Conhecimento base da Rádio Web Justiça Potiguar (Artistas ideais por estilo)
ESTILOS_SUGESTOES = {
    "MPB / CONTEMPORÂNEO": ["Liniker", "Luedji Luna", "Baco Exu do Blues", "Tiago Iorc", "Silva", "Anavitória", "Xenia França", "Céu", "Rubel"],
    "REGIONAL NORDESTINA": ["Alceu Valença", "Geraldo Azevedo", "Elba Ramalho", "Fagner", "Flávio José", "Santanna Cantador", "Xangai", "Vital Farias", "Maciel Melo"],
    "JAZZ / INSTRUMENTAL": ["Baden Powell", "Hamilton de Holanda", "Yamandu Costa", "João Donato", "Cama de Gato", "Hermeto Pascoal"],
    "BOSSA NOVA": ["Tom Jobim", "João Gilberto", "Vinicius de Moraes", "Nara Leão", "Stan Getz", "Toquinho", "Elis Regina"],
    "POP / ROCK INTERNACIONAL": ["Coldplay", "U2", "Queen", "The Beatles", "Fleetwood Mac", "Dire Straits", "Pink Floyd", "The Police"],
    "ROCK NACIONAL": ["Legião Urbana", "Skank", "Jota Quest", "Paralamas do Sucesso", "Titãs", "Engenheiros do Hawaii", "Barão Vermelho"],
}

# Mapeia os estilos CRUSADOS DO BANCO (minúsculos) para as chaves de sugestão acima.
# Case-insensitive e por substring, para absorver variações de grafia do ZaraRadio/BUTT.
_ESTILO_MAP = {
    "mpb": "MPB / CONTEMPORÂNEO",
    "instrumental": "JAZZ / INSTRUMENTAL",
    "jazz": "JAZZ / INSTRUMENTAL",
    "bossa": "BOSSA NOVA",
    "regional": "REGIONAL NORDESTINA",
    "forró": "REGIONAL NORDESTINA",
    "forro": "REGIONAL NORDESTINA",
    "sertanejo": "REGIONAL NORDESTINA",
    "rock": "ROCK NACIONAL",
    "pop internacional": "POP / ROCK INTERNACIONAL",
    "pop": "POP / ROCK INTERNACIONAL",
}


def _mapear_estilo(estilo_bd: str):
    """Converte um estilo vindo do BD para uma chave de ESTILOS_SUGESTOES (ou None)."""
    if not estilo_bd:
        return None
    e = estilo_bd.strip().lower()
    if e in _ESTILO_MAP:
        return _ESTILO_MAP[e]
    # Fallback por substring (ex.: "mpb clássico" -> mpb)
    for chave, destino in _ESTILO_MAP.items():
        if chave in e:
            return destino
    return None


class MusicRecommender:
    def __init__(self, log_dir: str = r"D:\RADIO\LOG ZARARADIO"):
        self.log_dir = log_dir

    def analyze_last_days(self, days: int = 5):
        """
        Analisa os logs dos últimos X dias para identificar estilos e artistas dominantes.
        """
        hoje = now_local()
        arquivos_log = []
        for i in range(days):
            data_str = (hoje - timedelta(days=i)).strftime("%Y-%m-%d")
            caminho = os.path.join(self.log_dir, f"{data_str}.log")
            if os.path.exists(caminho):
                arquivos_log.append(caminho)

        if not arquivos_log:
            logger.warning("[Recommender] Nenhum log encontrado para análise.")
            return {"top_styles": [], "top_artists": []}

        caminhos_tocados = []
        for log in arquivos_log:
            try:
                # ZaraRadio geralmente usa codificação cp1252
                with open(log, "r", encoding="cp1252", errors="ignore") as f:
                    for line in f:
                        parts = line.strip().split("\t")
                        if len(parts) >= 3 and parts[1].lower() == "início":
                            if r"D:\RADIO\MUSICAS" in parts[2].upper():
                                caminhos_tocados.append(parts[2])
            except Exception as e:
                logger.debug(f"Erro ao ler log {log}: {e}")

        # Cruza caminhos com o Banco de Dados para saber o ESTILO
        db = SessionLocal()
        try:
            estilos_contagem = Counter()
            artistas_contagem = Counter()

            # Pega uma amostra significativa
            amostra = caminhos_tocados[-2000:]
            for path in amostra:
                musica = db.query(Musica).filter(Musica.caminho == path).first()
                if musica:
                    estilos_contagem[musica.estilo.upper()] += 1
                    artistas_contagem[musica.artista.upper()] += 1

            return {
                "top_styles": estilos_contagem.most_common(5),
                "top_artists": artistas_contagem.most_common(10)
            }
        finally:
            db.close()

    def generate_recommendations(self, analysis: dict) -> list[dict]:
        """
        Gera uma lista de sugestões dinâmicas (Artista - Música) baseadas na análise.
        Estratégia em 2 camadas (sem mocks — usa dados reais do BD e dos logs):
          1. Para cada estilo dominante, sugere artistas-base do conhecimento da rádio
             que ainda faltam no acervo (count < LIMITE).
          2. Para cada artista que TOCOU muito mas tem poucas faixas cadastradas,
             sugere baixar mais do mesmo (curadoria baseada em audiência real).
        """
        recs = []
        db = SessionLocal()
        try:
            top_styles = [s[0] for s in analysis.get("top_styles", [])]
            top_artists = [a[0] for a in analysis.get("top_artists", [])]

            LIMITE_FAIXAS = 8  # abaixo disso, vale a pena complementar o acervo

            # --- Camada 1: artistas-base por estilo dominante ---
            estilos_mapeados = set()
            for estilo_bd in top_styles:
                chave = _mapear_estilo(estilo_bd)
                if not chave or chave in estilos_mapeados:
                    continue
                estilos_mapeados.add(chave)
                artistas_base = ESTILOS_SUGESTOES.get(chave, [])
                for art in artistas_base:
                    count = db.query(Musica).filter(Musica.artista.ilike(f"%{art}%")).count()
                    if count < LIMITE_FAIXAS:
                        recs.append({
                            "estilo": chave,
                            "artista": art,
                            "sugestao": f"{art} - melhores músicas",
                            "motivo": f"Estilo '{estilo_bd}' dominante nos logs. Acervo tem só {count} faixas de {art}."
                        })

            # --- Camada 2: artistas que tocaram muito mas faltam faixas ---
            # Pega os top_artists que tocaram, cruza com o acervo e sugere complementar.
            for art in top_artists:
                # pula artistas 'Desconhecido' ou muito curtos
                if not art or art in ("DESCONHECIDO",) or len(art) < 3:
                    continue
                count = db.query(Musica).filter(Musica.artista.ilike(f"%{art}%")).count()
                if 0 < count < LIMITE_FAIXAS:
                    recs.append({
                        "estilo": "REPERTÓRIO ATUAL",
                        "artista": art.title(),
                        "sugestao": f"{art.title()} - discografia selecionada",
                        "motivo": f"Artista tocou bastante na grade mas o acervo tem só {count} faixas. Complementar repertório."
                    })

            # Embaralha levemente para não ser sempre a mesma ordem
            random.shuffle(recs)

            return recs[:15]
        finally:
            db.close()


recommender_instance = MusicRecommender()
