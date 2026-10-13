"""
Низкоуровневый HTTP-клиент к Ollama (или любому OpenAI-совместимому бэкенду).

Отвечает ТОЛЬКО за транспорт: доступность, список моделей, /api/chat.
Никакой логики агента здесь нет — это в agent.py.
"""

from __future__ import annotations

from typing import Any, Iterable

import requests

from .config import BrainConfig


class BrainClientError(RuntimeError):
    """Ошибка транспорта или бэкенда."""


class BrainClient:
    """Клиент к Ollama HTTP API.

    Пример:
        client = BrainClient()
        if client.is_available():
            reply = client.chat([{"role": "user", "content": "привет"}])
    """

    def __init__(self, config: BrainConfig | None = None):
        self.config = config or BrainConfig.from_env()

    # ---------- Health / модели ----------

    def is_available(self) -> bool:
        """True, если бэкенд отвечает на /api/tags за разумное время."""
        try:
            r = requests.get(f"{self.config.base_url}/api/tags", timeout=3)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def list_models(self) -> list[str]:
        """Список имён установленных моделей."""
        try:
            r = requests.get(f"{self.config.base_url}/api/tags", timeout=5)
            r.raise_for_status()
        except requests.RequestException as e:
            raise BrainClientError(f"Backend недоступен: {e}") from e

        data = r.json()
        models = data.get("models", [])
        return [m.get("name", "") for m in models if m.get("name")]

    def has_model(self, name: str) -> bool:
        """Есть ли модель (сравнение по префиксу — llama3.2 == llama3.2:latest)."""
        short = name.split(":")[0]
        return any(m.split(":")[0] == short for m in self.list_models())

    # ---------- Chat ----------

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Один вызов /api/chat. Возвращает сырой ответ Ollama.

        messages: [{"role": "system"|"user"|"assistant"|"tool", "content": "...", ...}, ...]
        tools:    список JSON-схем инструментов (Ollama tools format)
        """
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }
        if tools:
            payload["tools"] = tools

        try:
            r = requests.post(
                f"{self.config.base_url}/api/chat",
                json=payload,
                timeout=self.config.timeout,
            )
            r.raise_for_status()
        except requests.RequestException as e:
            raise BrainClientError(f"Chat запрос упал: {e}") from e

        return r.json()

    # ---------- Утилиты ----------

    @staticmethod
    def extract_text(response: dict[str, Any]) -> str:
        """Вытащить текст ассистента из ответа Ollama."""
        msg = response.get("message") or {}
        return msg.get("content", "") or ""

    @staticmethod
    def extract_tool_calls(response: dict[str, Any]) -> list[dict[str, Any]]:
        """Вытащить список tool_calls (может быть пустым)."""
        msg = response.get("message") or {}
        calls = msg.get("tool_calls") or []
        return list(calls) if isinstance(calls, Iterable) else []