import logging
import google.generativeai as genai
from typing import Optional
import os

logger = logging.getLogger("OmniCore.GeminiService")

class GeminiService:
    def __init__(self, api_key: Optional[str] = None):
        # Tenta carregar do arquivo se não fornecido
        if not api_key:
            try:
                with open("config/gdrive_api_key.txt", "r") as f:
                    api_key = f.read().strip()
            except Exception:
                api_key = os.getenv("GOOGLE_API_KEY")

        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.enabled = True
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

        prompt = (
            f"Classifique o estilo/humor da música '{title}' do artista '{artist}'. "
            f"Escolha APENAS uma das seguintes categorias: 'Ensolarado', 'Sombrio', 'Foco'. "
            f"Responda apenas com a palavra da categoria."
        )

        try:
            # Nota: O SDK do Gemini é síncrono por padrão, mas podemos rodar em thread se necessário.
            # Para este worker, rodar síncrono no loop async do worker está ok se não for massivo.
            response = self.model.generate_content(prompt)
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
