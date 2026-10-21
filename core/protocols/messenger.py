"""
AIX OS — Messenger (#AI-4).

Быстрый оффчейн-мессенджер. Сообщения не пишутся в блокчейн,
а хранятся в JSON и летают через API ноды (мгновенно, без комиссий).

v3: медиа-вложения (фото) через /media/upload.
"""
import json
import time
import uuid
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional


@dataclass
class Message:
    id: str
    sender: str
    recipient: str
    text: str
    timestamp: float

    # --- Метаданные ---
    reply_to: str = ""
    forwarded_from: str = ""
    read_by: dict = field(default_factory=dict)
    reactions: list = field(default_factory=list)
    edited_text: str = ""
    edited_at: float = 0.0
    deleted_for: list = field(default_factory=list)
    deleted_for_all: bool = False
    pinned: bool = False
    pinned_at: float = 0.0

    # --- Медиа (фото/файл) ---
    media_id: str = ""       # имя файла в data/media/
    media_mime: str = ""     # image/png, image/jpeg, ...
    media_size: int = 0      # байты

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        allowed = {f.name for f in cls.__dataclass_fields__.values()}
        clean = {k: v for k, v in data.items() if k in allowed}
        return cls(**clean)

    def effective_text(self) -> str:
        return self.edited_text or self.text

    def visible_for(self, address: str) -> bool:
        if self.deleted_for_all:
            return False
        if address in self.deleted_for:
            return False
        return True

    def has_media(self) -> bool:
        return bool(self.media_id)


class MessengerManager:
    def __init__(self, storage_path):
        self.storage_path = Path(storage_path)
        self.messages: list[Message] = []
        self._by_id: dict[str, Message] = {}
        self._load()

    def _load(self):
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("messages", []):
                m = Message.from_dict(item)
                self.messages.append(m)
                self._by_id[m.id] = m
        except Exception as e:
            print(f"WARN: messenger load error: {e}")

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.storage_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                {"messages": [m.to_dict() for m in self.messages]},
                f, ensure_ascii=False, indent=2,
            )
        tmp.replace(self.storage_path)

    def _register(self, msg: Message):
        self.messages.append(msg)
        self._by_id[msg.id] = msg
        self._save()

    # =========================================================================
    # ОТПРАВКА
    # =========================================================================

    def send(
        self,
        sender: str,
        recipient: str,
        text: str,
        reply_to: str = "",
        forwarded_from: str = "",
        media_id: str = "",
        media_mime: str = "",
        media_size: int = 0,
    ) -> Message:
        msg = Message(
            id=str(uuid.uuid4()),
            sender=sender,
            recipient=recipient,
            text=text,
            timestamp=time.time(),
            reply_to=reply_to,
            forwarded_from=forwarded_from,
            media_id=media_id,
            media_mime=media_mime,
            media_size=media_size,
        )
        self._register(msg)
        return msg

    def get_by_id(self, message_id: str) -> Optional[Message]:
        return self._by_id.get(message_id)

    # =========================================================================
    # ЧТЕНИЕ
    # =========================================================================

    def get_dialogs(self, address: str) -> list[dict]:
        dialogs: dict[str, Message] = {}
        unread: dict[str, int] = {}
        for m in self.messages:
            if not m.visible_for(address):
                continue
            if m.sender != address and m.recipient != address:
                continue
            peer = m.recipient if m.sender == address else m.sender
            if peer not in dialogs or m.timestamp > dialogs[peer].timestamp:
                dialogs[peer] = m
            if m.sender != address and address not in m.read_by:
                unread[peer] = unread.get(peer, 0) + 1

        result = []
        for peer, last_msg in dialogs.items():
            d = last_msg.to_dict()
            d["text"] = last_msg.effective_text()
            result.append({
                "peer": peer,
                "last_message": d,
                "unread": unread.get(peer, 0),
            })
        result.sort(key=lambda x: x["last_message"]["timestamp"], reverse=True)
        return result

    def get_chat(self, address1: str, address2: str,
                 for_viewer: Optional[str] = None) -> list[Message]:
        chat = []
        for m in self.messages:
            if not (
                (m.sender == address1 and m.recipient == address2) or
                (m.sender == address2 and m.recipient == address1)
            ):
                continue
            if for_viewer and not m.visible_for(for_viewer):
                continue
            chat.append(m)
        chat.sort(key=lambda m: m.timestamp)
        return chat

    # =========================================================================
    # ПРОЧИТАНО
    # =========================================================================

    def mark_read(self, message_id: str, reader: str) -> tuple[bool, Optional[Message]]:
        m = self._by_id.get(message_id)
        if m is None:
            return False, None
        if reader in m.read_by:
            return True, m
        m.read_by[reader] = time.time()
        self._save()
        return True, m

    def mark_chat_read(self, address1: str, address2: str,
                       reader: str) -> list[Message]:
        changed: list[Message] = []
        for m in self.messages:
            if (m.sender == address1 and m.recipient == address2
                    and reader not in m.read_by):
                m.read_by[reader] = time.time()
                changed.append(m)
        if changed:
            self._save()
        return changed

    # =========================================================================
    # РЕАКЦИИ
    # =========================================================================

    def add_reaction(self, message_id: str, emoji: str,
                     by: str) -> tuple[bool, Optional[Message]]:
        m = self._by_id.get(message_id)
        if m is None:
            return False, None
        m.reactions = [r for r in m.reactions if r.get("by") != by]
        m.reactions.append({"emoji": emoji, "by": by, "at": time.time()})
        self._save()
        return True, m

    def remove_reaction(self, message_id: str,
                        by: str) -> tuple[bool, Optional[Message]]:
        m = self._by_id.get(message_id)
        if m is None:
            return False, None
        before = len(m.reactions)
        m.reactions = [r for r in m.reactions if r.get("by") != by]
        if len(m.reactions) == before:
            return False, m
        self._save()
        return True, m

    # =========================================================================
    # РЕДАКТИРОВАНИЕ
    # =========================================================================

    def edit(self, message_id: str, new_text: str,
             by: str) -> tuple[bool, Optional[Message]]:
        m = self._by_id.get(message_id)
        if m is None:
            return False, None
        if m.sender != by:
            return False, m
        m.edited_text = new_text
        m.edited_at = time.time()
        self._save()
        return True, m

    # =========================================================================
    # УДАЛЕНИЕ
    # =========================================================================

    def delete_for_me(self, message_id: str,
                      by: str) -> tuple[bool, Optional[Message]]:
        m = self._by_id.get(message_id)
        if m is None:
            return False, None
        if by not in m.deleted_for:
            m.deleted_for.append(by)
            self._save()
        return True, m

    def delete_for_all(self, message_id: str,
                       by: str) -> tuple[bool, Optional[Message]]:
        m = self._by_id.get(message_id)
        if m is None:
            return False, None
        if m.sender != by:
            return False, m
        m.deleted_for_all = True
        self._save()
        return True, m

    # =========================================================================
    # PIN
    # =========================================================================

    def pin(self, message_id: str) -> tuple[bool, Optional[Message]]:
        m = self._by_id.get(message_id)
        if m is None:
            return False, None
        m.pinned = True
        m.pinned_at = time.time()
        self._save()
        return True, m

    def unpin(self, message_id: str) -> tuple[bool, Optional[Message]]:
        m = self._by_id.get(message_id)
        if m is None:
            return False, None
        m.pinned = False
        self._save()
        return True, m

    def pinned_in_chat(self, address1: str, address2: str) -> list[Message]:
        return [
            m for m in self.messages
            if m.pinned and (
                (m.sender == address1 and m.recipient == address2) or
                (m.sender == address2 and m.recipient == address1)
            )
        ]