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
    "MPB / CONTEMPORÂNEO": ["Liniker", "Luedji Luna", "Baco Exu do Blues", "Tiago Iorc", "Silva", "Anavitória", "Xenia França", "Céu", "Rubel"],
    "REGIONAL NORDESTINA": ["Alceu Valença", "Geraldo Azevedo", "Elba Ramalho", "Fagner", "Flávio José", "Santanna Cantador", "Xangai", "Vital Farias", "Maciel Melo"],
    "JAZZ / INSTRUMENTAL": ["Baden Powell", "Hamilton de Holanda", "Yamandu Costa", "João Donato", "Cama de Gato", "Hermeto Pascoal"],
    "BOSSA NOVA": ["Tom Jobim", "João Gilberto", "Vinicius de Moraes", "Nara Leão", "Stan Getz", "Toquinho", "Elis Regina"],
    "POP / ROCK INTERNACIONAL": ["Coldplay", "U2", "Queen", "The Beatles", "Fleetwood Mac", "Dire Straits", "Pink Floyd", "The Police"],
    "ROCK NACIONAL": ["Legião Urbana", "Skank", "Jota Quest", "Paralamas do Sucesso", "Titãs", "Engenheiros do Hawaii", "Barão Vermelho"],
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
        """
        recs = []
        db = SessionLocal()
        try:
            top_styles = [s[0] for s in analysis.get("top_styles", [])]
            if not top_styles:
                # Se não houver análise, usa estilos padrão do perfil
                top_styles = list(ESTILOS_SUGESTOES.keys())[:3]
            
            for estilo in top_styles:
                artistas_base = ESTILOS_SUGESTOES.get(estilo, [])
                for art in artistas_base:
                    # Verifica o que já temos desse artista
                    count = db.query(Musica).filter(Musica.artista.ilike(f"%{art}%")).count()
                    
                    if count < 8:
                        # Variação de termos de busca para evitar duplicidade de 'Greatest Hits'
                        sugestoes_termos = [
                            f"{art} melhores músicas",
                            f"{art} discografia selecionada",
                            f"{art} sucessos mpb",
                            f"{art} rádio mix"
                        ]
                        # Escolhe um termo baseado no dia para variar a lista
                        idx = datetime.now().day % len(sugestoes_termos)
                        termo = sugestoes_termos[idx]

                        recs.append({
                            "estilo": estilo,
                            "artista": art,
                            "sugestao": f"{art} - {termo}",
                            "motivo": f"Estilo '{estilo}' detectado nos logs. Temos apenas {count} faixas de {art}."
                        })
            
            # Embaralha levemente para não ser sempre a mesma ordem
            import random
            random.shuffle(recs)
            
            return recs[:15]
        finally:
            db.close()


recommender_instance = MusicRecommender()
