"""
AIX Brain — встроенный AI-напарник AIX OS.

Публичный API:
    BrainConfig   — конфиг (модель, URL, промпт)
    BrainClient   — низкоуровневый HTTP-клиент к Ollama
    BrainTools    — реестр инструментов + JSON-схемы
    MemoryBridge  — мост в core/protocols/ai_memory
    BaseSigner    — интерфейс подписанта транзакций
    NullSigner    — заглушка (API и по умолчанию): отправка запрещена
    CLISigner     — интерактивный y/N + подпись + POST /send
    BrainAgent    — высокоуровневый оркестратор
"""

from .config import BrainConfig
from .client import BrainClient, BrainClientError
from .tools import BrainTools, TOOL_SCHEMAS
from .memory_bridge import MemoryBridge
from .signer import BaseSigner, NullSigner, CLISigner
from .agent import BrainAgent

__all__ = [
    "BrainConfig",
    "BrainClient",
    "BrainClientError",
    "BrainTools",
    "TOOL_SCHEMAS",
    "MemoryBridge",
    "BaseSigner",
    "NullSigner",
    "CLISigner",
    "BrainAgent",
]

__version__ = "0.2.0"