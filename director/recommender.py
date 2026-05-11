import os
import glob
import logging
from datetime import datetime, timedelta
from collections import Counter
from core.database import SessionLocal
from core.models import Musica
from director.profile import PROFILE

logger = logging.getLogger("OmniCore.MusicRecommender")

# Conhecimento base da Rádio Web Justiça Potiguar (Artistas ideais por estilo)
ESTILOS_SUGESTOES = {
    "MPB / CONTEMPORÂNEO": ["Liniker", "Luedji Luna", "Baco Exu do Blues", "Tiago Iorc", "Silva", "Anavitória"],
    "REGIONAL NORDESTINA": ["Alceu Valença", "Geraldo Azevedo", "Elba Ramalho", "Fagner", "Flávio José", "Santanna Cantador"],
    "JAZZ / INSTRUMENTAL": ["Baden Powell", "Hamilton de Holanda", "Yamandu Costa", "João Donato"],
    "BOSSA NOVA": ["Tom Jobim", "João Gilberto", "Vinicius de Moraes", "Nara Leão", "Stan Getz"],
    "POP / ROCK INTERNACIONAL": ["Coldplay", "U2", "Queen", "The Beatles", "Fleetwood Mac"],
    "ROCK NACIONAL": ["Legião Urbana", "Skank", "Jota Quest", "Paralamas do Sucesso", "Titãs"],
}

class MusicRecommender:
    def __init__(self, log_dir: str = r"D:\RADIO\LOG ZARARADIO"):
        self.log_dir = log_dir

    def analyze_last_days(self, days: int = 5):
        """
        Analisa os logs dos últimos X dias para identificar estilos e artistas dominantes.
        """
        hoje = datetime.now()
        arquivos_log = []
        for i in range(days):
            data_str = (hoje - timedelta(days=i)).strftime("%Y-%m-%d")
            caminho = os.path.join(self.log_dir, f"{data_str}.log")
            if os.path.exists(caminho):
                arquivos_log.append(caminho)

        if not arquivos_log:
            logger.warning("[Recommender] Nenhum log encontrado para análise.")
            return {"styles": {}, "artists": {}}

        caminhos_tocados = []
        for log in arquivos_log:
            try:
                with open(log, "r", encoding="cp1252", errors="ignore") as f:
                    for line in f:
                        parts = line.strip().split("\t")
                        if len(parts) >= 3 and parts[1].lower() == "início":
                            if r"D:\RADIO\MUSICAS" in parts[2].upper():
                                caminhos_tocados.append(parts[2])
            except: pass

        # Cruza caminhos com o Banco de Dados para saber o ESTILO
        db = SessionLocal()
        try:
            estilos_contagem = Counter()
            artistas_contagem = Counter()
            
            # Pega uma amostra para performance
            amostra = caminhos_tocados[-1000:] 
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
        Gera uma lista de sugestões proativas (Artista - Música) baseadas na análise.
        """
        recs = []
        db = SessionLocal()
        try:
            top_styles = [s[0] for s in analysis.get("top_styles", [])]
            
            for estilo in top_styles:
                artistas_sugeridos = ESTILOS_SUGESTOES.get(estilo, [])
                for art in artistas_sugeridos:
                    # Verifica se o artista já está muito presente no acervo
                    count = db.query(Musica).filter(Musica.artista.ilike(f"%{art}%")).count()
                    if count < 5: # Se temos poucas músicas dele, sugerimos mais
                        recs.append({
                            "estilo": estilo,
                            "artista": art,
                            "sugestao": f"{art} - Greatest Hits", # Termo de busca genérico
                            "motivo": f"Estilo '{estilo}' está em alta e temos apenas {count} faixas de {art}."
                        })
            
            # Limita a 15 sugestões para não sobrecarregar a UI
            return recs[:15]
        finally:
            db.close()

recommender_instance = MusicRecommender()
