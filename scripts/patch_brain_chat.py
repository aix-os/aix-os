"""
Патч cli/main.py: обновляет функцию cmd_brain_chat.

Что меняется:
- алиасы выхода: exit | quit | q | stop | выход
- пустой ответ модели не попадает в историю + сообщение пользователю
- обновлённая подсказка

Идемпотентен. Бэкап: cli/main.py.chat.bak при первом патче.
Если якорь не найден — печатает FATAL и НЕ трогает файл.

Запуск:
    .venv\\Scripts\\python.exe scripts\\patch_brain_chat.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "main.py"

MARKER = "exit | quit | q | stop | выход"

OLD_FUNC = '''def cmd_brain_chat(a):
    from ai.brain import BrainAgent, BrainConfig, CLISigner, NullSigner
    cfg = BrainConfig.from_env()
    if a.model:
        cfg = cfg.with_model(a.model)
    signer = CLISigner(a.wallet, cfg.node_url) if getattr(a, "wallet", None) else NullSigner()
    agent = BrainAgent(cfg, signer=signer)
    if not agent.client.is_available():
        print(f"{Fore.RED}\\u274c Ollama недоступен на {cfg.base_url}")
        return 1
    print(f"{Fore.MAGENTA}\\U0001f9e0 AIX Brain -- интерактивный режим ({cfg.model})")
    print(f"   {Fore.YELLOW}exit/quit -- выход, reset -- очистить историю{Fore.RESET}")
    while True:
        try:
            line = input(f"{Fore.CYAN}вы> {Fore.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.lower() in ("exit", "quit", "q"):
            break
        if line.lower() == "reset":
            agent.reset()
            print(f"{Fore.YELLOW}История очищена.{Fore.RESET}")
            continue
        try:
            answer = agent.ask(line)
        except Exception as e:
            print(f"{Fore.RED}\\u274c {e}")
            continue
        print(f"{Fore.GREEN}\\U0001f9e0 {answer}\\n")
    return 0
'''

NEW_FUNC = '''def cmd_brain_chat(a):
    from ai.brain import BrainAgent, BrainConfig, CLISigner, NullSigner
    cfg = BrainConfig.from_env()
    if a.model:
        cfg = cfg.with_model(a.model)
    signer = CLISigner(a.wallet, cfg.node_url) if getattr(a, "wallet", None) else NullSigner()
    agent = BrainAgent(cfg, signer=signer)
    if not agent.client.is_available():
        print(f"{Fore.RED}\\u274c Ollama недоступен на {cfg.base_url}")
        print(f"   Установи: https://ollama.com")
        print(f"   Затем:    ollama pull {cfg.model}")
        return 1
    print(f"{Fore.MAGENTA}\\U0001f9e0 AIX Brain -- интерактивный режим ({cfg.model})")
    print(f"   {Fore.YELLOW}exit | quit | stop | выход -- выход, "
          f"reset -- очистить историю{Fore.RESET}")
    while True:
        try:
            line = input(f"{Fore.CYAN}вы> {Fore.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.lower() in ("exit", "quit", "q", "stop", "выход"):
            break
        if line.lower() == "reset":
            agent.reset()
            print(f"{Fore.YELLOW}История очищена.{Fore.RESET}")
            continue
        try:
            answer = agent.ask(line)
        except Exception as e:
            print(f"{Fore.RED}\\u274c {e}")
            continue
        if not answer or not answer.strip():
            print(f"{Fore.YELLOW}\\U0001f9e0 (пустой ответ модели — история сброшена, "
                  f"попробуй переформулировать){Fore.RESET}")
            continue
        print(f"{Fore.GREEN}\\U0001f9e0 {answer}\\n")
    return 0
'''


def main() -> int:
    if not CLI.exists():
        print(f"[FATAL] {CLI} не найден")
        return 1

    src = CLI.read_text(encoding="utf-8")

    if MARKER in src:
        print("[cli/main.py] уже пропатчен — пропуск")
        return 0

    if OLD_FUNC not in src:
        print("[FATAL] Не найден якорь cmd_brain_chat.")
        print("  Скинь мне текущий cli/main.py — пересчитаю якорь.")
        return 1

    bak = CLI.with_suffix(CLI.suffix + ".chat.bak")
    bak.write_bytes(CLI.read_bytes())
    print(f"[cli/main.py] backup -> {bak.name}")

    src = src.replace(OLD_FUNC, NEW_FUNC, 1)
    CLI.write_text(src, encoding="utf-8")

    print("[cli/main.py] OK: cmd_brain_chat обновлён")
    print()
    print("\u2705 Патч завершён.")
    print("   Перезапуск нод не нужен (CLI читается при каждом запуске).")
    print("   Проверь:")
    print("     .venv\\Scripts\\python.exe cli\\main.py brain chat --wallet alice")
    return 0


if __name__ == "__main__":
    sys.exit(main())