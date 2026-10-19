"""
AIX OS — mDNS Discovery (Автоматический поиск нод).
Каждая нода кричит в локальную сеть: "Я AIX-нода на порту XXXX!".
И слушает, кто ещё кричит. Если находит нового — добавляет в PeerManager.
"""

import socket
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ServiceListener
import config


class AixNodeListener(ServiceListener):
    def __init__(self, peer_manager, self_port: int):
        self.peer_manager = peer_manager
        self.self_port = self_port

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if not info:
            return
        addresses = info.parsed_addresses()
        if not addresses:
            return
        ip = addresses[0]
        port = info.port
        if port == self.self_port:
            return
        url = f"http://{ip}:{port}"
        if url not in self.peer_manager.peers:
            print(f"[mDNS] 🟢 Найдена нода: {url}")
            ok, msg = self.peer_manager.add(url)
            if ok:
                print(f"[mDNS] ✅ Добавлена в пиры: {url}")

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass


class MdnsDiscovery:
    def __init__(self, port: int, peer_manager):
        self.port = port
        self.peer_manager = peer_manager
        self.zc = None
        self.service_info = None
        self.browser = None

    def start(self):
        hostname = socket.gethostname()
        try:
            local_ip = socket.gethostbyname(hostname)
            if local_ip.startswith("127."):
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
        except Exception:
            local_ip = "127.0.0.1"

        ip_bytes = socket.inet_aton(local_ip)
        self.zc = Zeroconf()
        service_type = "_aix-node._tcp.local."
        service_name = f"AIX-NODE-{self.port}.{service_type}"

        self.service_info = ServiceInfo(
            type_=service_type,
            name=service_name,
            addresses=[ip_bytes],
            port=self.port,
            properties={"version": config.VERSION, "port": str(self.port)},
            server=f"{hostname}.local.",
        )

        print(f"[mDNS] 📢 Объявляю себя в сети: {local_ip}:{self.port}")
        self.zc.register_service(self.service_info)

        listener = AixNodeListener(self.peer_manager, self.port)
        self.browser = ServiceBrowser(self.zc, service_type, listener)
        print("[mDNS] 👂 Слушаю локальную сеть...")

    def stop(self):
        if self.zc:
            if self.service_info:
                self.zc.unregister_service(self.service_info)
            self.zc.close()
            print("[mDNS] 🛑 Служба обнаружения остановлена")