"""AIX OS — WebSocket Connection Manager.

Управляет активными WS-соединениями по AIX-адресам.
Typing-статусы — в памяти, TTL 5 секунд.
"""
from __future__ import annotations

import asyncio
import time
from typing import Optional

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()
        self._typing: dict[str, dict[str, float]] = {}  # {address: {peer: expires_at}}

    async def connect(self, ws: WebSocket, address: str):
        await ws.accept()
        async with self._lock:
            self.active.setdefault(address, set()).add(ws)

    def disconnect(self, ws: WebSocket, address: str):
        if address in self.active:
            self.active[address].discard(ws)
            if not self.active[address]:
                del self.active[address]

    async def send_to(self, address: str, message: dict):
        for ws in list(self.active.get(address, set())):
            try:
                await ws.send_json(message)
            except Exception:
                pass

    async def broadcast(self, message: dict, exclude: Optional[set[str]] = None):
        exclude = exclude or set()
        for addr, sockets in list(self.active.items()):
            if addr in exclude:
                continue
            for ws in list(sockets):
                try:
                    await ws.send_json(message)
                except Exception:
                    pass

    def online(self, address: str) -> bool:
        return bool(self.active.get(address))

    def online_list(self) -> list[str]:
        return list(self.active.keys())

    # ----- Typing (ephemeral, in-memory) -----

    def set_typing(self, address: str, peer: str, is_typing: bool):
        if is_typing:
            self._typing.setdefault(address, {})[peer] = time.time() + 5.0
        else:
            self._typing.get(address, {}).pop(peer, None)

    def is_typing(self, address: str, peer: str) -> bool:
        exp = self._typing.get(address, {}).get(peer, 0)
        return exp > time.time()

    def cleanup_typing(self):
        now = time.time()
        for addr in list(self._typing.keys()):
            for peer in list(self._typing[addr].keys()):
                if self._typing[addr][peer] <= now:
                    del self._typing[addr][peer]
            if not self._typing[addr]:
                del self._typing[addr]