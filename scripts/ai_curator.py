import os
import logging
import ollama
from typing import Optional
from sqlalchemy.orm import Session
from core.models import Musica

logger = logging.getLogger("OmniCore.AICurator")

class AICurator:
    """Motor de Curadoria por IA para gerar conteúdos e intros de rádio usando Ollama Local."""
    
    def __init__(self, model: str = "qwen2.5:7b"):
        self.model = model
        self.enabled = True
        
    def generate_track_intro(self, musica: Musica) -> str:
        """Gera um texto curto de introdução para o locutor via Ollama."""
        if not self.enabled:
            return f"E agora, vamos ouvir {musica.titulo} de {musica.artista}."
            
        prompt = (
            f"Você é um locutor de rádio experiente e carismático. "
            f"Gere uma frase de introdução de no máximo 20 segundos para a música "
            f"'{musica.titulo}' do artista '{musica.artista}'. "
            f"Inclua uma curiosidade rápida sobre a música ou o artista se souber. "
            f"Tom de voz: Profissional, rádio FM, animado. "
            f"Responda APENAS com o texto da locução, sem comentários adicionais."
        )
        
        try:
            response = ollama.generate(model=self.model, prompt=prompt)
            intro = response.get('response', "").strip()
            # Limpa aspas se a IA colocar
            if intro.startswith('"') and intro.endswith('"'):
                intro = intro[1:-1]
            return intro
        except Exception as e:
            logger.error(f"Erro ao chamar Ollama: {e}")
            return f"No ar agora, {musica.titulo} com {musica.artista}."

    def enrich_acervo_batch(self, db: Session, limit: int = 5):
        """Enriquece o banco de dados com insights da IA para faixas que ainda não possuem."""
        # Pega as músicas que ainda não têm insight e não são jingles/vinhetas (heurística simples)
        pendentes = (
            db.query(Musica)
            .filter(Musica.ai_insight == None)
            .filter(Musica.estilo != "vinheta")
            .filter(Musica.estilo != "spot")
            .limit(limit)
            .all()
        )
        
        count = 0
        for musica in pendentes:
            logger.info(f"Ollama: Gerando insight para [{musica.id}] {musica.titulo}")
            insight = self.generate_track_intro(musica)
            if insight:
                musica.ai_insight = insight
                count += 1
        
        if count > 0:
            db.commit()
            
        return count

# Instância global
ai_curator_instance = AICurator()


