"""
AIX Brain Agent — оркестратор: LLM ↔ инструменты ↔ ответ.
"""

from __future__ import annotations

import json
from typing import Any

from .client import BrainClient, BrainClientError
from .config import BrainConfig
from .tools import BrainTools
from .memory_bridge import MemoryBridge
from .signer import BaseSigner, NullSigner


MAX_TOOL_ITERATIONS = 5


class BrainAgent:
    """Высокоуровневый агент. Один инстанс = одна сессия диалога."""

    def __init__(
        self,
        config: BrainConfig | None = None,
        client: BrainClient | None = None,
        tools: BrainTools | None = None,
        signer: BaseSigner | None = None,
    ):
        self.config = config or BrainConfig.from_env()
        self.client = client or BrainClient(self.config)
        self.memory = MemoryBridge()
        self.signer = signer or NullSigner()
        self.tools = tools or BrainTools(self.config, self.memory, self.signer)
        self.history: list[dict[str, Any]] = []

    # ---------- публичный API ----------

    def reset(self) -> None:
        self.history = []

    def health(self) -> dict[str, Any]:
        return {
            "backend_available": self.client.is_available(),
            "backend_url": self.config.base_url,
            "model": self.config.model,
            "model_installed": self._safe_has_model(),
            "models_available": self._safe_list_models(),
            "memory_available": self.memory.available(),
            "tools": self.tools.names(),
            "node_url": self.config.node_url,
            "signer": self.signer.name,
            "signer_enabled": self.signer.enabled,
        }

    def ask(self, user_message: str) -> str:
        if not user_message.strip():
            return ""

        messages = self._build_messages(user_message)
        final_text = ""

        for _ in range(MAX_TOOL_ITERATIONS):
            response = self.client.chat(messages, tools=self.tools.schemas())
            calls = self.client.extract_tool_calls(response)

            if not calls:
                final_text = self.client.extract_text(response)
                break

            assistant_msg = response.get("message") or {}
            messages.append(assistant_msg)

            for call in calls:
                name, args = self._parse_tool_call(call)
                result = self.tools.execute(name, args)
                messages.append(
                    {
                        "role": "tool",
                        "name": name,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
        else:
            final_text = (
                "Достигнут предел вызовов инструментов. "
                "Последний ответ модели пустой — возможно, бэкенд не отвечает."
            )

        # Если ответ пустой — не пишем пустоту в историю, чтобы модель
        # на следующем вопросе не «висела» на пустом сообщении.
        if final_text.strip():
            self.history.append({"role": "user", "content": user_message})
            self.history.append({"role": "assistant", "content": final_text})
        else:
            # Сбрасываем историю — модель запуталась, начинаем с чистого листа
            self.history = []

        return final_text

    def remember(
        self,
        title: str,
        kind: str = "THOUGHT",
        priority: str = "NORMAL",
        body: str = "",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        return self.memory.remember(
            title=title, kind=kind, priority=priority, body=body, tags=tags
        )

    # ---------- внутреннее ----------

    def _build_messages(self, user_message: str) -> list[dict[str, Any]]:
        msgs: list[dict[str, Any]] = [
            {"role": "system", "content": self.config.system_prompt}
        ]
        msgs.extend(self.history)
        msgs.append({"role": "user", "content": user_message})
        return msgs

    @staticmethod
    def _parse_tool_call(call: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        fn = call.get("function") or {}
        name = fn.get("name") or call.get("name") or ""
        raw_args = fn.get("arguments", call.get("arguments", {}))
        if isinstance(raw_args, str):
            try:
                args = json.loads(raw_args) if raw_args.strip() else {}
            except json.JSONDecodeError:
                args = {}
        elif isinstance(raw_args, dict):
            args = raw_args
        else:
            args = {}
        return name, args

    def _safe_has_model(self) -> bool:
        try:
            return self.client.has_model(self.config.model)
        except BrainClientError:
            return False

    def _safe_list_models(self) -> list[str]:
        try:
            return self.client.list_models()
        except BrainClientError:
            return []