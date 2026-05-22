import logging
from google import genai
from typing import Optional
from core.config_loader import get_secret
import os

from services.rate_limiter import RateLimiter

logger = logging.getLogger("OmniCore.GeminiService")

# Limita chamadas para evitar estouro da cota de API do Gemini (ex: 15 chamadas/min)
_gemini_limiter = RateLimiter(max_calls=15, period_seconds=60)

class GeminiService:
    def __init__(self, api_key: Optional[str] = None):
        # Tenta carregar do ambiente via config_loader ou fallback para arquivo local
        if not api_key:
            api_key = (
                get_secret("GEMINI_API_KEY")
                or get_secret("GDRIVE_API_KEY")
                or get_secret("GOOGLE_API_KEY")
            )
            if not api_key:
                try:
                    with open("config/gdrive_api_key.txt", "r") as f:
                        api_key = f.read().strip()
                except Exception:
                    pass

        if api_key:
            try:
                self.client = genai.Client(api_key=api_key)
                self.model_name = 'gemini-2.5-flash'
                self.enabled = True
            except Exception as e:
                logger.error(f"Erro ao inicializar cliente Gemini: {e}")
                self.enabled = False
        else:
            logger.warning("Google API Key não encontrada. GeminiService desativado.")
            self.enabled = False

    async def classify_mood(self, artist: str, title: str) -> Optional[str]:
        """
        Classifica o humor da música com base no artista e título.
        Retorna: 'Ensolarado', 'Sombrio', 'Foco' ou None.
        """
        if not self.enabled:
            return None

        # Aguarda autorização da cota de requisição (Rate Limit)
        _gemini_limiter.wait_and_acquire()

        prompt = (
            f"Classifique o estilo/humor da música '{title}' do artista '{artist}'. "
            f"Escolha APENAS uma das seguintes categorias: 'Ensolarado', 'Sombrio', 'Foco'. "
            f"Responda apenas com a palavra da categoria."
        )

        try:
            # Novo SDK do Gemini (google-genai)
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            mood = response.text.strip()
            
            # Validação simples
            valid_moods = ['Ensolarado', 'Sombrio', 'Foco']
            if mood in valid_moods:
                return mood
            
            # Se a IA enrolar, tenta extrair
            for m in valid_moods:
                if m.lower() in mood.lower():
                    return m
                    
            return None
        except Exception as e:
            logger.error(f"Erro ao classificar mood com Gemini: {e}")
            return None

gemini_service = GeminiService()
