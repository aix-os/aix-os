"""
AIX OS — Peer (соседняя нода).
"""

import time
from dataclasses import dataclass
from typing import Optional

import requests


@dataclass
class Peer:
    """Соседняя нода AIX."""

    url: str
    last_seen: float = 0.0
    height: int = 0
    difficulty: int = 0
    version: str = ""
    is_alive: bool = False
    total_work: int = 0

    def ping(self, timeout: float = 5.0) -> bool:
        try:
            r = requests.get(f"{self.url}/status", timeout=timeout)
            if r.status_code == 200:
                data = r.json()
                self.height = data.get("height", 0)
                self.difficulty = data.get("difficulty", 0)
                self.version = data.get("version", "?")
                self.total_work = data.get("total_work", 0)
                self.last_seen = time.time()
                self.is_alive = True
                return True
        except requests.RequestException:
            pass
        self.is_alive = False
        return False

    def get_chain(self, timeout: float = 10.0) -> Optional[dict]:
        try:
            r = requests.get(f"{self.url}/sync/chain", timeout=timeout)
            if r.status_code == 200:
                return r.json()
        except requests.RequestException:
            pass
        return None

    def get_state(self, timeout: float = 10.0) -> Optional[dict]:
        """Скачать полное состояние протоколов (gift/timelock/sbt)."""
        try:
            r = requests.get(f"{self.url}/sync/state", timeout=timeout)
            if r.status_code == 200:
                return r.json()
        except requests.RequestException:
            pass
        return None

    def send_state_event(self, event: dict, from_peer: str = "",
                         timeout: float = 10.0) -> bool:
        """Отправить одно событие состояния (gift/timelock/medal)."""
        try:
            r = requests.post(
                f"{self.url}/sync/state/event",
                json={"event": event, "from_peer": from_peer},
                timeout=timeout,
            )
            return r.status_code == 200
        except requests.RequestException:
            return False

    def send_block(self, block_dict: dict, from_peer: str = "",
                   timeout: float = 10.0) -> bool:
        try:
            r = requests.post(
                f"{self.url}/sync/block",
                json={"block": block_dict, "from_peer": from_peer},
                timeout=timeout,
            )
            return r.status_code == 200
        except requests.RequestException:
            return False

    def send_transaction(self, tx_dict: dict, timeout: float = 10.0) -> bool:
        try:
            r = requests.post(f"{self.url}/sync/tx", json=tx_dict, timeout=timeout)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def register_self(self, self_url: str, timeout: float = 5.0) -> bool:
        try:
            r = requests.post(f"{self.url}/peers/register",
                              json={"url": self_url}, timeout=timeout)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def __repr__(self) -> str:
        status = "✅" if self.is_alive else "❌"
        return f"Peer({self.url}, height={self.height}, work={self.total_work}, {status})"