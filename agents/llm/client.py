import json
import logging
import httpx
from typing import Dict, Any, List, Optional
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class LocalLLMClient:
    """
    Client for local open-source LLM (Ollama / OpenAI-compatible v1 API).
    Includes deterministic fallback reasoner when local model server is offline.
    """

    def __init__(self):
        self.base_url = settings.LLM_BASE_URL.rstrip("/")
        self.model = settings.LLM_MODEL
        self.timeout = settings.LLM_TIMEOUT

    def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 1024
    ) -> Optional[str]:
        """
        Sends request to Ollama / OpenAI-compatible chat completions endpoint.
        """
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            with httpx.Client(timeout=float(self.timeout)) as client:
                res = client.post(url, json=payload, headers={"Content-Type": "application/json"})
                if res.status_code == 200:
                    data = res.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.warning(f"LLM API returned status {res.status_code}: {res.text}")
        except Exception as e:
            logger.info(f"Local LLM endpoint ({url}) not reachable ({e}). Engaging deterministic reasoning layer.")

        return None

llm_client = LocalLLMClient()
