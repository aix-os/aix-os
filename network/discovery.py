"""AIX OS — mDNS Discovery (правильный асинхронный)."""
import socket
import psutil
from zeroconf import ServiceInfo, ServiceStateChange
from zeroconf.asyncio import AsyncZeroconf, AsyncServiceBrowser, AsyncServiceInfo

class AixNodeListener:
    def __init__(self, aiozc: AsyncZeroconf, peer_manager, self_port: int):
        self.aiozc = aiozc
        self.peer_manager = peer_manager
        self.self_port = self_port

    async def _handle_add(self, zeroconf, type_, name):
        info = AsyncServiceInfo(type_, name)
        if not await info.async_request(zeroconf, 3000):
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
            ok, msg = self.peer_manager.add(url, ping=False)
            if ok:
                print(f"[mDNS] ✅ Добавлена в пиры: {url}")

    def __call__(self, zeroconf, service_type, name, state_change):
        if state_change is ServiceStateChange.Added:
            import asyncio
            asyncio.create_task(self._handle_add(zeroconf, service_type, name))


def get_local_ip():
    """Возвращает правильный локальный IP (Wi-Fi/Ethernet), игнорируя Docker/WSL."""
    try:
        for name, addrs in psutil.net_if_addrs().items():
            # Пропускаем виртуальные адаптеры
            if "vEthernet" in name or "Loopback" in name or "WSL" in name or "Virtual" in name:
                continue
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    ip = addr.address
                    if ip.startswith("192.168.") or ip.startswith("10."):
                        return ip
    except Exception:
        pass
    return "127.0.0.1"


class MdnsDiscovery:
    def __init__(self, port: int, peer_manager):
        self.port = port
        self.peer_manager = peer_manager
        self.aiozc = None
        self.service_info = None
        self.browser = None

    async def start(self):
        self.aiozc = AsyncZeroconf()
        ip = get_local_ip()
        hostname = socket.gethostname()
        
        self.service_info = ServiceInfo(
            "_aix-node._tcp.local.",
            f"AIX-Node-{self.port}._aix-node._tcp.local.",
            addresses=[socket.inet_aton(ip)],
            port=self.port,
            properties={"version": "0.1.0"},
            server=f"{hostname}.local.",
        )
        await self.aiozc.async_register_service(self.service_info)
        print(f"[mDNS] 📢 Объявляю себя в сети: {ip}:{self.port}")
        
        listener = AixNodeListener(self.aiozc, self.peer_manager, self.port)
        self.browser = AsyncServiceBrowser(self.aiozc.zeroconf, "_aix-node._tcp.local.", handlers=[listener])
        print("[mDNS] 👂 Слушаю локальную сеть...")

    async def stop(self):
        if self.browser:
            await self.browser.async_cancel()
        if self.aiozc:
            await self.aiozc.async_unregister_service(self.service_info)
            await self.aiozc.async_close()
