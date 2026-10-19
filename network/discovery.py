"""AIX OS — mDNS Discovery (правильный асинхронный, для FastAPI/uvicorn)."""
import socket
from zeroconf import ServiceInfo, ServiceListener, ServiceStateChange
from zeroconf.asyncio import AsyncZeroconf, AsyncServiceBrowser, AsyncServiceInfo
import config


class AixNodeListener(ServiceListener):
    def __init__(self, aiozc: AsyncZeroconf, peer_manager, self_port: int):
        self.aiozc = aiozc
        self.peer_manager = peer_manager
        self.self_port = self_port

    def __call__(self, zeroconf, service_type, name, state_change):
        """AsyncServiceBrowser вызывает listener как callable."""
        import asyncio
        if state_change is ServiceStateChange.Added:
            asyncio.create_task(self._handle_add(zeroconf, service_type, name))

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
            ok, msg = self.peer_manager.add(url)
            if ok:
                print(f"[mDNS] ✅ Добавлена в пиры: {url}")

    def add_service(self, zc, type_, name):
        pass  # не используется, т.к. вызывается __call__

    def update_service(self, zc, type_, name):
        pass

    def remove_service(self, zc, type_, name):
        pass


class MdnsDiscovery:
    def __init__(self, port: int, peer_manager):
        self.port = port
        self.peer_manager = peer_manager
        self.aiozc = None
        self.service_info = None
        self.browser = None

    async def start(self):
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
        self.aiozc = AsyncZeroconf()
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
        await self.aiozc.async_register_service(self.service_info)

        listener = AixNodeListener(self.aiozc, self.peer_manager, self.port)
        self.browser = AsyncServiceBrowser(
            self.aiozc.zeroconf, service_type, handlers=[listener]
        )
        print("[mDNS] 👂 Слушаю локальную сеть...")

    async def stop(self):
        if self.aiozc:
            if self.browser:
                await self.browser.async_cancel()
            await self.aiozc.async_unregister_service(self.service_info)
            await self.aiozc.async_close()
            print("[mDNS] 🛑 Служба обнаружения остановлена")