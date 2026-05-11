import json
import logging
import os
import tempfile
from datetime import datetime
from typing import Any

import requests
from sqlalchemy.orm import Session

from core.database import SessionLocal
from core.models import Musica
from director import grade_rules as GR
from director.auditor import ProgrammingAuditor
from director.profile import PROFILE

logger = logging.getLogger("OmniCore.ActorCritic")

DEFAULT_MEMORY_PATH = os.path.join(GR.CFG.get("pasta_programacao", "."), "memoria_workers.json")
OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")


class ActorCriticDirector:
    def __init__(self, memory_path: str | None = None, api_url: str | None = None, model: str | None = None):
        self.memory_path = memory_path or DEFAULT_MEMORY_PATH
        self.api_url = api_url or OLLAMA_API_URL
        self.model = model or OLLAMA_MODEL
        self.auditor = ProgrammingAuditor()

    def load_memory(self) -> dict[str, Any]:
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
            except Exception as e:
                logger.error(f"[ActorCritic] Falha ao carregar memória: {e}")
        return {"historico_penalidades": [], "score_total": 0}

    def save_memory(self, memory: dict[str, Any]) -> None:
        try:
            os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
            with open(self.memory_path, "w", encoding="utf-8") as f:
                json.dump(memory, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[ActorCritic] Falha ao salvar memória: {e}")

    def _available_tracks(self, db: Session, limit: int = 80) -> list[dict[str, Any]]:
        tracks = (
            db.query(Musica)
            .filter(Musica.redflag == False)
            .order_by(Musica.vezes_tocada.asc(), Musica.ultima_reproducao.asc())
            .limit(limit)
            .all()
        )

        result: list[dict[str, Any]] = []
        for musica in tracks:
            if not musica.caminho:
                continue
            result.append({
                "caminho": musica.caminho,
                "titulo": musica.titulo,
                "artista": musica.artista,
                "estilo": musica.estilo,
                "energia": musica.energia,
                "duracao": musica.duracao,
            })
        return result

    def _build_prompt(self, tracks: list[dict[str, Any]], memory: dict[str, Any], hora_inicio: int, mood: str | None) -> str:
        energy_rules = PROFILE["dayparting"].get("MADRUGADA", {})
        if mood and mood in PROFILE["dayparting"]:
            energy_rules = PROFILE["dayparting"][mood]

        constraints = PROFILE["constraints"]
        quotas = PROFILE["quotas"]
        part = f"Hora de início: {hora_inicio:02d}H. Mood: {mood or GR.CFG.get('mood_padrao', 'Ensolarado')}"

        memory_text = "" if not memory.get("historico_penalidades") else (
            "Erros recentes a não repetir:\n" + "\n".join(f"- {item}" for item in memory["historico_penalidades"][-8:])
        )

        track_list = [
            {
                "caminho": item["caminho"],
                "artista": item["artista"],
                "titulo": item["titulo"],
                "estilo": item["estilo"],
                "energia": item["energia"],
            }
            for item in tracks
        ]

        prompt = (
            "Você é o Agente Curador da Rádio. Seu trabalho é gerar uma playlist para um bloco de 2h "
            "respeitando regras de dayparting e quotas. Seja extremamente estrito e retorne apenas JSON válido.\n"
            f"{part}\n"
            "Regras importantes:\n"
            f"- Não repita o mesmo artista em um intervalo de {constraints['artist_separation_count']} músicas.\n"
            f"- Não repita a mesma faixa em um intervalo de {constraints['track_separation_count']} músicas.\n"
            f"- Inclua aproximadamente 1 música regional a cada {int(1/quotas['regional_ratio'])} faixas.\n"
            f"- Utilize dayparting de energia; prefira energias do período.\n"
            "- Retorne apenas um array JSON de caminhos absolutos, sem texto extra.\n"
        )

        if memory_text:
            prompt += f"\n{memory_text}\n"

        prompt += "\nMúsicas disponíveis para seleção (use apenas os caminhos listados):\n"
        prompt += json.dumps(track_list, ensure_ascii=False, indent=2)
        prompt += "\n\nResposta esperada: [\"caminho1\", \"caminho2\", ...]"
        return prompt

    def _parse_selection(self, raw: Any) -> list[str]:
        if isinstance(raw, list):
            return [str(item) for item in raw if isinstance(item, (str,))]
        if not isinstance(raw, str):
            return []

        raw = raw.strip()
        if raw.startswith("[") and raw.endswith("]"):
            try:
                parsed = json.loads(raw)
                return [str(item) for item in parsed if isinstance(item, str)]
            except json.JSONDecodeError:
                pass

        # Fallback: extrai linhas que parecem caminhos
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        return [line for line in lines if line.startswith("/") or ":\\" in line]

    def query_ollama(self, tracks: list[dict[str, Any]], memory: dict[str, Any], hora_inicio: int, mood: str | None) -> list[str]:
        prompt = self._build_prompt(tracks, memory, hora_inicio, mood)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=40)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                raw = data.get("response") or data.get("output") or data
            else:
                raw = data

            selection = self._parse_selection(raw)
            return selection
        except Exception as e:
            logger.error(f"[ActorCritic] Falha ao consultar Ollama: {e}")
            return []

    def _write_playlist(self, paths: list[str], path: str) -> bool:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="cp1252", errors="replace") as f:
                f.write("#EXTM3U\n")
                for item in paths:
                    f.write(f"{item}\n")
            return True
        except Exception as e:
            logger.error(f"[ActorCritic] Erro ao escrever playlist '{path}': {e}")
            return False

    def evaluate_playlist(self, paths: list[str]) -> tuple[int, list[Any]]:
        if not paths:
            return -1, ["Playlist vazia"]

        with tempfile.NamedTemporaryFile("w", encoding="cp1252", delete=False, suffix=".m3u") as tmp:
            tmp.write("#EXTM3U\n")
            for caminho in paths:
                tmp.write(f"{caminho}\n")
            tmp_path = tmp.name

        try:
            violations = self.auditor.audit_file(tmp_path)
        except Exception as e:
            logger.error(f"[ActorCritic] Erro ao avaliar playlist temporária: {e}")
            violations = [str(e)]
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        if not violations:
            return 1, []

        return max(-5, -len(violations)), violations

    def run_cycle(self, hora_inicio: int, mood: str | None = None, output_path: str | None = None) -> bool:
        memory = self.load_memory()
        db = SessionLocal()
        try:
            tracks = self._available_tracks(db)
        finally:
            db.close()

        if not tracks:
            logger.warning("[ActorCritic] Nenhuma faixa disponível para geração.")
            return False

        selection = self.query_ollama(tracks, memory, hora_inicio, mood)
        if not selection:
            logger.warning("[ActorCritic] Seleção do Ollama vazia. Cancelando ciclo.")
            return False

        score, violations = self.evaluate_playlist(selection)
        memory["score_total"] = int(memory.get("score_total", 0)) + score
        if violations:
            memory.setdefault("historico_penalidades", []).append(
                f"Bloco {hora_inicio:02d}H: {violations[0]}"
            )
            memory["historico_penalidades"] = memory["historico_penalidades"][-10:]

        self.save_memory(memory)

        if score <= 0:
            logger.warning(f"[ActorCritic] Playlist reprovada pelo crítico: {violations}")
            return False

        if output_path:
            if not self._write_playlist(selection, output_path):
                return False

        logger.info(f"[ActorCritic] Playlist aprovada com score {score}.")
        return True

    def memory_summary(self) -> dict[str, Any]:
        memory = self.load_memory()
        return {
            "score_total": memory.get("score_total", 0),
            "historico_penalidades": memory.get("historico_penalidades", []),
        }


actor_critic_instance = ActorCriticDirector()
