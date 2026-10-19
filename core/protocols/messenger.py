"""
AIX OS — Messenger (#AI-4).

Быстрый оффчейн-мессенджер. Сообщения не пишутся в блокчейн,
а хранятся в JSON и летают через API ноды (мгновенно, без комиссий).
"""
import json
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

@dataclass
class Message:
    id: str
    sender: str
    recipient: str
    text: str
    timestamp: float

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        return cls(**data)

class MessengerManager:
    def __init__(self, storage_path):
        self.storage_path = Path(storage_path)
        self.messages: list[Message] = []
        self._load()

    def _load(self):
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("messages", []):
                self.messages.append(Message.from_dict(item))
        except Exception as e:
            print(f"WARN: messenger load error: {e}")

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.storage_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"messages": [m.to_dict() for m in self.messages]}, f, ensure_ascii=False, indent=2)
        tmp.replace(self.storage_path)

    def send(self, sender: str, recipient: str, text: str) -> Message:
        msg = Message(
            id=str(uuid.uuid4()),
            sender=sender,
            recipient=recipient,
            text=text,
            timestamp=time.time(),
        )
        self.messages.append(msg)
        self._save()
        return msg

    def get_dialogs(self, address: str) -> list[dict]:
        """Возвращает список уникальных собеседников с последним сообщением."""
        dialogs = {}
        for m in self.messages:
            if m.sender == address or m.recipient == address:
                peer = m.recipient if m.sender == address else m.sender
                if peer not in dialogs or m.timestamp > dialogs[peer].timestamp:
                    dialogs[peer] = m
        
        result = []
        for peer, last_msg in dialogs.items():
            result.append({
                "peer": peer,
                "last_message": last_msg.to_dict()
            })
        result.sort(key=lambda x: x["last_message"]["timestamp"], reverse=True)
        return result

    def get_chat(self, address1: str, address2: str) -> list[Message]:
        """История переписки между двумя адресами."""
        chat = [
            m for m in self.messages
            if (m.sender == address1 and m.recipient == address2) or
               (m.sender == address2 and m.recipient == address1)
        ]
        chat.sort(key=lambda m: m.timestamp)
        return chat