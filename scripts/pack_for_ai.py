"""AIX OS — Pack full brief for AI.

Собирает один файл AI_BRIEF_FULL.md:
  1. AI_BRIEF.md        — шапка + CONTEXT.md + AI Memory + состояние
  2. Дерево проекта     — структура папок и файлов
  3. Содержимое файлов  — код + конфиги + доки

Режимы:
    --core   только ключевые файлы (~250 KB) - для чата
    --slim   только бриф + структура (~30 KB)
    (по умолчанию) всё (~880 KB)

Запуск:
    python scripts/pack_for_ai.py --core
    python scripts/pack_for_ai.py --slim
    python scripts/pack_for_ai.py
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
PY = ROOT / ".venv" / "Scripts" / "python.exe"
if not PY.exists():
    PY = Path(sys.executable)


EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "env", "__pycache__", "node_modules",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".idea", ".vscode",
    ".dart_tool", "build", "target", "dist", ".gradle",
    "web_backup", ".flutter-plugins", ".plugin_symlinks",
}
EXCLUDE_DIR_PREFIXES = ("data_backup_",)

EXCLUDE_FILE_SUFFIXES = (
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".exe", ".bin",
    ".bak", ".backup", ".log", ".tmp",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".pdf",
    ".zip", ".tar", ".gz", ".db", ".sqlite", ".lock",
)
EXCLUDE_FILE_NAMES = {
    "AIX_OS_FULL_DUMP.txt", "AI_BRIEF.md", "AI_BRIEF_FULL.md",
    "project-tree.txt", ".DS_Store",
}

# CORE — только эти файлы идут в --core режиме
CORE_FILES = [
    "config.py",
    "CONTEXT.md",
    "README.md",
    "ROADMAP.md",
    "requirements.txt",
    "core/chain.py",
    "core/block.py",
    "core/transaction.py",
    "core/mempool.py",
    "core/wallet.py",
    "core/protocols/__init__.py",
    "core/protocols/ai_memory.py",
    "core/protocols/poc.py",
    "core/protocols/state_sync.py",
    "network/server.py",
    "network/peer.py",
    "network/peer_manager.py",
    "cli/main.py",
    "storage/db.py",
    "web/index.html",
    "tests/test_ai_memory.py",
    "scripts/ai_brief.py",
    "scripts/ai_remember.py",
    "scripts/pack_for_ai.py",
]

PRIORITY_ORDER = CORE_FILES + [
    "core/protocols/gift_link.py",
    "core/protocols/time_lock.py",
    "core/protocols/sbt.py",
    "core/protocols/lottery.py",
    "core/protocols/dead_mans_switch.py",
    "core/protocols/aix_id.py",
    "core/protocols/burn_to_mint.py",
    "core/protocols/contacts.py",
    "core/protocols/swap.py",
    "core/governance/dao.py",
    "crypto/address.py",
    "crypto/keys.py",
    "crypto/hash.py",
]

INCLUDE_SUFFIXES = {
    ".py", ".md", ".html", ".js", ".css", ".json", ".yaml", ".yml",
    ".toml", ".txt", ".cfg", ".ini", ".dart", ".ps1", ".sh", ".bat",
}
INCLUDE_NAMES = {".gitignore", ".gitattributes", "Dockerfile", "LICENSE"}


def should_exclude_dir(name: str) -> bool:
    if name in EXCLUDE_DIRS:
        return True
    return any(name.startswith(p) for p in EXCLUDE_DIR_PREFIXES)


def should_exclude_file(path: Path) -> bool:
    if path.name in EXCLUDE_FILE_NAMES:
        return True
    if path.name.endswith(".wallet.json"):
        return True
    return any(path.name.endswith(s) for s in EXCLUDE_FILE_SUFFIXES)


def is_includeable(path: Path) -> bool:
    if path.name in INCLUDE_NAMES:
        return True
    return path.suffix.lower() in INCLUDE_SUFFIXES


def build_tree(root: Path, max_depth: int = 4) -> str:
    lines = [f"{root.name}/"]

    def walk(d: Path, prefix: str = "", depth: int = 0):
        if depth >= max_depth:
            return
        try:
            entries = sorted(
                [e for e in d.iterdir()],
                key=lambda e: (not e.is_dir(), e.name.lower()),
            )
        except PermissionError:
            return
        entries = [
            e for e in entries
            if not (e.is_dir() and should_exclude_dir(e.name))
            and not (e.is_file() and should_exclude_file(e))
        ]
        for i, entry in enumerate(entries):
            last = i == len(entries) - 1
            pointer = "`-- " if last else "|-- "
            lines.append(f"{prefix}{pointer}{entry.name}{'/' if entry.is_dir() else ''}")
            if entry.is_dir():
                walk(entry, prefix + ("    " if last else "|   "), depth + 1)

    walk(root)
    return "\n".join(lines)


def collect_files(root: Path, core_only: bool = False) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        skip = False
        for parent in path.parents:
            if parent == root:
                break
            if should_exclude_dir(parent.name):
                skip = True
                break
        if skip or should_exclude_file(path) or not is_includeable(path):
            continue
        rel = path.relative_to(root).as_posix()
        if core_only and rel not in CORE_FILES:
            continue
        files.append(path)

    def sort_key(p: Path):
        rel = p.relative_to(root).as_posix()
        try:
            prio = PRIORITY_ORDER.index(rel)
        except ValueError:
            prio = len(PRIORITY_ORDER)
        return (prio, rel)

    return sorted(files, key=sort_key)


def render_file_section(root: Path, path: Path) -> str:
    rel = path.relative_to(root).as_posix()
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        content = f"<<READ ERROR: {e}>>"
    lines = content.count("\n") + 1
    size = len(content.encode("utf-8"))
    return (
        "\n" + "=" * 80 + "\n"
        f"FILE: {rel}\n"
        f"Size: {size} bytes | Lines: {lines}\n"
        + "=" * 80 + "\n"
        + content
        + "\n"
    )


def regenerate_brief() -> str:
    brief_path = ROOT / "AI_BRIEF.md"
    print("  Running ai_brief.py...")
        import os
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        result = subprocess.run(
            [str(PY), str(ROOT / "scripts" / "ai_brief.py"), "--output", str(brief_path)],
            cwd=str(ROOT), check=True, capture_output=True,
            encoding="utf-8", errors="replace", env=env, timeout=60,
        )
        if result.stdout:
            print(f"    {result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"  WARN: ai_brief.py exit={e.returncode}")
        if e.stderr:
            print("  STDERR:")
            for line in e.stderr.strip().splitlines()[-15:]:
                print(f"    {line}")
    except Exception as e:
        print(f"  WARN: {e}")
    if brief_path.exists():
        return brief_path.read_text(encoding="utf-8")
    return "_AI_BRIEF.md not generated_"


def pack(slim: bool = False, core_only: bool = False) -> str:
    out = []

    print("[1/3] Generating AI_BRIEF.md...")
    out.append(regenerate_brief())

    print("[2/3] Building project tree...")
    out.append("\n\n" + "=" * 80 + "\n")
    out.append("PROJECT STRUCTURE\n")
    out.append("=" * 80 + "\n\n```\n")
    out.append(build_tree(ROOT))
    out.append("\n```\n")

    if slim:
        return "".join(out)

    mode = "CORE" if core_only else "FULL"
    print(f"[3/3] Collecting files ({mode})...")
    files = collect_files(ROOT, core_only=core_only)
    print(f"   Files: {len(files)}")

    out.append("\n\n" + "=" * 80 + "\n")
    out.append(f"FILE CONTENTS ({mode})\n")
    out.append("=" * 80 + "\n")

    total_lines = 0
    total_bytes = 0
    for f in files:
        section = render_file_section(ROOT, f)
        out.append(section)
        total_lines += section.count("\n")
        total_bytes += len(section.encode("utf-8"))

    out.append("\n" + "=" * 80 + "\n")
    out.append("END OF DUMP\n")
    out.append(f"Files: {len(files)}\n")
    out.append(f"Total lines: {total_lines}\n")
    out.append(f"Total bytes: {total_bytes}\n")
    out.append("=" * 80 + "\n")

    return "".join(out)


def main() -> int:
    p = argparse.ArgumentParser(description="AIX OS - Pack brief for AI")
    p.add_argument("--output", "-o", default="AI_BRIEF_FULL.md")
    p.add_argument("--slim", action="store_true",
                   help="Only brief + tree, no file contents")
    p.add_argument("--core", action="store_true",
                   help="Only core files (~250 KB) - fits in chat")
    args = p.parse_args()

    print("=" * 50)
    print("  AIX OS - PACK FOR AI")
    print("=" * 50)

    text = pack(slim=args.slim, core_only=args.core)

    out_path = ROOT / args.output
    out_path.write_text(text, encoding="utf-8")

    size_kb = out_path.stat().st_size / 1024
    print()
    print(f"Done: {out_path.name}")
    print(f"   Size: {size_kb:.1f} KB")
    print(f"   Lines: {text.count(chr(10))}")
    print()
    if not args.slim and not args.core and size_kb > 200:
        print(f"WARN: {size_kb:.0f} KB too big for chat.")
        print(f"   Use: python scripts/pack_for_ai.py --core")
    return 0


if __name__ == "__main__":
    sys.exit(main())