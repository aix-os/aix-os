"""
AIX OS — Менеджер пиров.
"""

import json
from pathlib import Path
from typing import Optional

from network.peer import Peer


class PeerManager:
    """Реестр пиров ноды с сохранением на диск."""

    def __init__(self, self_url: str, storage_path: Optional[str] = None):
        self.self_url = self_url.rstrip("/")
        self.peers: dict[str, Peer] = {}
        self.storage_path = Path(storage_path) if storage_path else None
        if self.storage_path:
            self._load()

    def _load(self) -> None:
        if not self.storage_path or not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for url in data.get("peers", []):
                url = url.rstrip("/")
                if url and url != self.self_url:
                    self.peers[url] = Peer(url=url)
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️  Не удалось загрузить пиров: {e}")

    def _save(self) -> None:
        if not self.storage_path:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.storage_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"peers": list(self.peers.keys())}, f, ensure_ascii=False, indent=2)
        tmp.replace(self.storage_path)

    def add(self, url: str, ping: bool = True) -> tuple[bool, str]:
        url = url.rstrip("/")
        if url == self.self_url:
            return False, "Нельзя добавить себя"
        if url in self.peers:
            if ping:
                self.peers[url].ping()
            return True, "Пир уже в списке"
        peer = Peer(url=url)
        if ping and not peer.ping():
            return False, f"Нода {url} не отвечает"
        self.peers[url] = peer
        self._save()
        return True, "OK"

    def register_from_remote(self, url: str) -> tuple[bool, str]:
        url = url.rstrip("/")
        if url == self.self_url:
            return False, "Себя регистрировать не нужно"
        if url in self.peers:
            return True, "Уже зарегистрирован"
        self.peers[url] = Peer(url=url)
        self._save()
        return True, "Зарегистрирован"

    def remove(self, url: str) -> bool:
        url = url.rstrip("/")
        removed = self.peers.pop(url, None) is not None
        if removed:
            self._save()
        return removed

    def exchange_peers(self):
        """Спрашиваем у текущих пиров, каких других пиров они знают, и добавляем их."""
        new_peers = set()
        for peer in list(self.peers.values()):
            if peer.is_alive:
                their_peers = peer.get_peers()
                if their_peers:
                    for u in their_peers:
                        u = u.rstrip("/")
                        if u != self.self_url and u not in self.peers:
                            new_peers.add(u)
        for u in new_peers:
            print(f"[PEX] 🔗 Новый пир от соседа: {u}")
            self.add(u, ping=False)

    def ping_all(self) -> dict:
        alive = sum(1 for p in list(self.peers.values()) if p.ping())
        return {"alive": alive, "dead": len(self.peers) - alive, "total": len(self.peers)}

    def broadcast_block(self, block_dict: dict, from_peer: str = "") -> int:
        count = 0
        for peer in list(self.peers.values()):
            if from_peer and peer.url.rstrip("/") == from_peer.rstrip("/"):
                continue
            if peer.send_block(block_dict, from_peer=self.self_url):
                count += 1
        return count

    def broadcast_transaction(self, tx_dict: dict) -> int:
        return sum(1 for p in list(self.peers.values()) if p.send_transaction(tx_dict))

    def broadcast_state_event(self, event: dict, from_peer: str = "") -> int:
        """Разослать событие состояния (gift/timelock/medal) всем пирам."""
        count = 0
        for peer in list(self.peers.values()):
            if from_peer and peer.url.rstrip("/") == from_peer.rstrip("/"):
                continue
            if peer.send_state_event(event, from_peer=self.self_url):
                count += 1
        return count

    def best_peer(self) -> Optional[Peer]:
        alive = [p for p in list(self.peers.values()) if p.is_alive]
        if not alive:
            return None
        return max(alive, key=lambda p: (p.total_work or 0, p.height))

    def to_list(self) -> list[dict]:
        return [
            {"url": p.url, "is_alive": p.is_alive, "height": p.height,
             "difficulty": p.difficulty, "version": p.version,
             "total_work": p.total_work, "last_seen": p.last_seen}
            for p in list(self.peers.values())
        ]

    def __len__(self) -> int:
        return len(self.peers)

    def __repr__(self) -> str:
        return f"PeerManager({len(self.peers)} peers, self={self.self_url})"