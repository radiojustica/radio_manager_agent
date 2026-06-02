import json
import logging
import inspect
from abc import abstractmethod
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, UTC

from core.worker_base import WorkerBase, WorkerResult
from core.reward import RewardStore
from services.gemini_service import gemini_service
import requests

logger = logging.getLogger("OmniCore.SubAgentBase")

class SubAgentBase(WorkerBase):
    """
    Classe base para Subagentes Autônomos baseados em LLM.
    Oferece suporte a loops de raciocínio CoT (Thought -> Tool -> Observation),
    registro dinâmico de ferramentas e fallbacks automáticos entre Gemini e Ollama.
    """
    def __init__(self, name: str, reward_store: RewardStore | None = None, config: dict[str, Any] | None = None):
        super().__init__(name=name, reward_store=reward_store, config=config)
        self.tools: Dict[str, Callable] = {}
        self._register_decorated_tools()
        
        # Carrega chaves ou configs específicas de IA
        self.model_preference = self.config.get("model_preference", "gemini")  # gemini ou ollama
        self.ollama_api_url = self.config.get("ollama_url", "http://localhost:11434/api/generate")
        self.ollama_model = self.config.get("ollama_model", "qwen2.5:7b")

    def _register_decorated_tools(self):
        """Varre os métodos da classe registrando os marcados com is_tool."""
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, "is_tool") and getattr(attr, "is_tool"):
                tool_name = attr_name
                self.tools[tool_name] = attr
                self.log_action("TOOL_REGISTERED", level="debug", tool=tool_name)

    def register_tool_func(self, name: str, func: Callable):
        """Registra uma função arbitrária como ferramenta."""
        self.tools[name] = func
        self.log_action("TOOL_REGISTERED", level="debug", tool=name)

    def _get_tools_metadata(self) -> List[Dict[str, Any]]:
        """Gera a descrição das ferramentas para o prompt do agente."""
        metadata = []
        for name, func in self.tools.items():
            doc = inspect.getdoc(func) or "Sem descrição."
            sig = str(inspect.signature(func))
            metadata.append({
                "name": name,
                "description": doc,
                "signature": sig
            })
        return metadata

    def query_llm(self, prompt: str, system_prompt: str) -> str:
        """Consulta o provedor de LLM configurado (Gemini com fallback para Ollama)."""
        # 1. Tentativa via Gemini se habilitado e preferido
        if self.model_preference == "gemini" and gemini_service.enabled:
            try:
                # Usando o cliente direto do GeminiService configurado na Fase 2
                response = gemini_service.client.models.generate_content(
                    model=gemini_service.model_name,
                    contents=prompt,
                    config={"system_instruction": system_prompt}
                )
                return response.text.strip()
            except Exception as e:
                self.log_error(e, "GEMINI_QUERY_FAILED_FALLBACK_OLLAMA")
        
        # 2. Fallback / Execução direta via Ollama Local
        payload = {
            "model": self.ollama_model,
            "prompt": f"System: {system_prompt}\n\nUser: {prompt}",
            "stream": False,
            "format": "json"
        }
        try:
            res = requests.post(self.ollama_api_url, json=payload, timeout=30)
            res.raise_for_status()
            data = res.json()
            return data.get("response", "").strip()
        except Exception as e:
            self.log_error(e, "OLLAMA_QUERY_FAILED")
            raise RuntimeError(f"Nenhum provedor de LLM disponível (Gemini/Ollama falharam): {e}")

    def run_agent_loop(self, task_description: str, system_prompt: str, max_steps: int = 5) -> Dict[str, Any]:
        """
        Executa o loop de raciocínio ReAct / CoT.
        Espera respostas no formato JSON estruturado:
        {
           "thought": "sua linha de raciocínio",
           "tool": "nome_da_ferramenta_ou_null",
           "args": { "argumento_nome": "valor" },
           "final_answer": { "status": "...", "result": ... } (se tool for null)
        }
        """
        self.log_action("AGENT_LOOP_START", task=task_description[:100])
        history = [f"Tarefa principal: {task_description}"]
        tools_desc = json.dumps(self._get_tools_metadata(), ensure_ascii=False, indent=2)
        
        full_system_prompt = (
            f"{system_prompt}\n\n"
            "Você é um subagente autônomo. Você pode chamar ferramentas locais para obter informações "
            "ou executar ações no sistema. Você DEVE responder estritamente no formato JSON abaixo a cada passo.\n"
            "Formatos aceitos:\n"
            "Para chamar uma ferramenta:\n"
            '{\n  "thought": "Explicação do que precisa fazer",\n  "tool": "nome_da_ferramenta",\n  "args": { "arg1": "val1" }\n}\n\n'
            "Para finalizar a tarefa:\n"
            '{\n  "thought": "Explicação final",\n  "tool": null,\n  "args": null,\n  "final_answer": { "status": "success/failed", "result": "sua resposta final ou dicionário" }\n}\n\n'
            f"Ferramentas Disponíveis:\n{tools_desc}\n"
        )

        for step in range(1, max_steps + 1):
            prompt = (
                f"Histórico e Observações anteriores:\n" + "\n".join(history) + 
                "\n\nQual é o seu próximo passo? Responda APENAS com o JSON estruturado."
            )
            
            self.log_action("AGENT_STEP_REQUEST", step=step)
            raw_response = self.query_llm(prompt, full_system_prompt)
            
            try:
                # Tenta limpar marcações de código markdown se o LLM incluir
                cleaned = raw_response.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
                
                response_data = json.loads(cleaned)
            except Exception as e:
                self.log_action("JSON_PARSE_ERROR", raw=raw_response[:200], err=str(e))
                history.append(f"Erro no passo {step}: Sua resposta não foi um JSON válido. Responda estritamente em JSON.")
                continue

            thought = response_data.get("thought", "")
            tool_name = response_data.get("tool")
            tool_args = response_data.get("args") or {}
            final_answer = response_data.get("final_answer")

            self.log_action("AGENT_THOUGHT", step=step, thought=thought)

            if tool_name:
                if tool_name in self.tools:
                    self.log_action("AGENT_CALL_TOOL", tool=tool_name, tool_args=tool_args)
                    try:
                        # Executa a ferramenta local
                        result = self.tools[tool_name](**tool_args)
                        obs = f"Passo {step}: Chamou ferramenta '{tool_name}' com {tool_args}. Resultado: {result}"
                        self.log_action("AGENT_TOOL_OBSERVATION", tool=tool_name, result_len=len(str(result)))
                    except Exception as e:
                        obs = f"Passo {step}: Erro ao executar ferramenta '{tool_name}': {e}"
                        self.log_error(e, f"TOOL_EXECUTION_FAILED_{tool_name}")
                else:
                    obs = f"Passo {step}: Erro. A ferramenta '{tool_name}' não existe."
                    self.log_action("AGENT_TOOL_NOT_FOUND", tool=tool_name)
                
                history.append(obs)
            elif final_answer:
                self.log_action("AGENT_FINAL_ANSWER", status=final_answer.get("status"))
                return final_answer
            else:
                # Nem ferramenta nem resposta final
                history.append(f"Passo {step}: Você não especificou uma ferramenta nem final_answer. Finalize ou chame uma ferramenta.")

        self.log_action("AGENT_MAX_STEPS_EXCEEDED", max_steps=max_steps)
        return {"status": "failed", "result": "Excedeu o número máximo de passos sem conclusão."}

def tool(func: Callable):
    """Decorador para marcar métodos como ferramentas do subagente."""
    func.is_tool = True
    return func
