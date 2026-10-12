"""AIX OS — авто-патчер DAO.

Применяет правки для интеграции DAO в:
  - network/server.py     (API эндпоинты)
  - cli/main.py           (команды aix dao ...)

Идемпотентный, с .bak-бэкапами.

Запуск:
    python scripts/patch_dao.py
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()


def log_ok(m):   print(f"\033[92mOK  {m}\033[0m")
def log_err(m):  print(f"\033[91mERR {m}\033[0m")
def log_info(m): print(f"\033[96m    {m}\033[0m")


def backup(p: Path):
    bak = p.with_suffix(p.suffix + ".bak")
    if not bak.exists():
        shutil.copy2(p, bak)
        log_info(f"backup: {bak.name}")


def insert_after(text, anchor, insert, marker):
    if marker in text:
        return text, False
    i = text.find(anchor)
    if i == -1:
        raise ValueError(f"anchor not found: {anchor[:60]!r}")
    return text[:i + len(anchor)] + insert + text[i + len(anchor):], True


def insert_before(text, anchor, insert, marker):
    if marker in text:
        return text, False
    i = text.find(anchor)
    if i == -1:
        raise ValueError(f"anchor not found: {anchor[:60]!r}")
    return text[:i] + insert + text[i:], True


def replace_once(text, old, new, marker):
    if marker in text:
        return text, False
    if old not in text:
        raise ValueError(f"not found: {old[:60]!r}")
    return text.replace(old, new, 1), True


# =============================================================================
# SERVER.PY
# =============================================================================

def patch_server():
    path = ROOT / "network" / "server.py"
    if not path.exists():
        log_err(f"not found: {path}")
        return
    backup(path)
    text = path.read_text(encoding="utf-8")

    # 1. import
    anchor = "from network.peer_manager import PeerManager"
    insert = "\nfrom core.governance.dao import DAOManager"
    text, _ = insert_after(text, anchor, insert, marker="from core.governance.dao import")

    # 2. Pydantic model
    anchor = "class AIRememberRequest(BaseModel):\n    text: str\n    kind: str = \"THOUGHT\"\n    priority: str = \"NORMAL\"\n    tags: list[str] = []\n    session: str = \"\"\n    chain_ref: str = \"\""
    insert = '''


class DAOCreateRequest(BaseModel):
    author: str
    title: str
    description: str
    kind: str = "TEXT"
    payload: dict = {}


class DAOVoteRequest(BaseModel):
    voter: str
    choice: str  # yes | no


class DAOCancelRequest(BaseModel):
    by: str'''
    text, _ = insert_after(text, anchor, insert, marker="class DAOCreateRequest")

    # 3. init dao_manager
    anchor = '    ai_memory = AIMemoryManager(ai_memory_path)'
    insert = '\n\n    dao_path = Path(data_file).parent / f"dao_{port}.json"\n    dao_manager = DAOManager(dao_path, blockchain=blockchain, sbt_manager=sbt_manager, poc_manager=poc_manager)'
    text, _ = insert_after(text, anchor, insert, marker="dao_manager = DAOManager")

    # 4. lifespan log
    anchor = '        print(f"[{port}] AI Memory: {ai_memory.count()} записей")'
    insert = '\n        print(f"[{port}] DAO: {len(dao_manager)} proposals")'
    text, _ = insert_after(text, anchor, insert, marker='DAO: {len(dao_manager)}')

    # 5. /status field
    old = '            "ai_memory_count": ai_memory.count(),\n        }'
    new = '            "ai_memory_count": ai_memory.count(),\n            "dao_count": len(dao_manager),\n        }'
    text, _ = replace_once(text, old, new, marker='"dao_count": len(dao_manager)')

    # 6. endpoints before P2P
    anchor = '''    # =========================================================================
    # P2P
    # =========================================================================
'''
    insert = '''    # =========================================================================
    # DAO (#13)
    # =========================================================================

    @app.get("/dao/stats")
    def dao_stats():
        return dao_manager.stats()

    @app.get("/dao/all")
    def dao_all(limit: int = 50):
        return {"count": limit, "proposals": [p.to_dict() for p in dao_manager.list_all(limit)]}

    @app.get("/dao/status/{status}")
    def dao_by_status(status: str):
        proposals = dao_manager.list_by_status(status)
        return {"status": status, "count": len(proposals),
                "proposals": [p.to_dict() for p in proposals]}

    @app.get("/dao/author/{address}")
    def dao_by_author(address: str):
        addr = resolve_who(address)
        proposals = dao_manager.list_by_author(addr)
        return {"author": addr, "count": len(proposals),
                "proposals": [p.to_dict() for p in proposals]}

    @app.get("/dao/{proposal_id}")
    def dao_info(proposal_id: str):
        p = dao_manager.get(proposal_id)
        if p is None:
            raise HTTPException(404, "Proposal not found")
        return p.to_dict()

    @app.post("/dao/create")
    def dao_create(req: DAOCreateRequest):
        author = resolve_who(req.author)
        ok, result = dao_manager.create_proposal(
            author=author,
            title=req.title,
            description=req.description,
            kind=req.kind,
            payload=req.payload,
        )
        if not ok:
            raise HTTPException(400, result)
        p = dao_manager.get(result)
        peer_manager.broadcast_state_event({"kind": "dao_proposal", "data": p.to_dict()})
        return {"status": "created", "id": p.id, "author": p.author,
                "kind": p.kind, "title": p.title,
                "voting_ends_at_height": p.voting_ends_at_height}

    @app.post("/dao/{proposal_id}/vote")
    def dao_vote(proposal_id: str, req: DAOVoteRequest):
        voter = resolve_who(req.voter)
        ok, msg = dao_manager.vote(proposal_id, voter, req.choice)
        if not ok:
            raise HTTPException(400, msg)
        p = dao_manager.get(proposal_id)
        peer_manager.broadcast_state_event({"kind": "dao_proposal", "data": p.to_dict()})
        return {"status": "voted", "id": proposal_id,
                "yes_weight": p.yes_weight(),
                "no_weight": p.no_weight(),
                "votes_count": p.votes_count(),
                "message": msg}

    @app.post("/dao/{proposal_id}/tally")
    def dao_tally(proposal_id: str):
        ok, msg = dao_manager.tally(proposal_id)
        if not ok:
            raise HTTPException(400, msg)
        p = dao_manager.get(proposal_id)
        peer_manager.broadcast_state_event({"kind": "dao_proposal", "data": p.to_dict()})
        return {"status": "tallied", "id": proposal_id,
                "proposal_status": p.status,
                "yes_weight": p.yes_weight(),
                "no_weight": p.no_weight()}

    @app.post("/dao/{proposal_id}/execute")
    def dao_execute(proposal_id: str):
        ok, msg = dao_manager.execute(proposal_id)
        if not ok:
            raise HTTPException(400, msg)
        p = dao_manager.get(proposal_id)
        peer_manager.broadcast_state_event({"kind": "dao_proposal", "data": p.to_dict()})
        return {"status": "executed", "id": proposal_id,
                "proposal_status": p.status,
                "tx_id": p.executed_tx_id,
                "message": msg}

    @app.post("/dao/{proposal_id}/cancel")
    def dao_cancel(proposal_id: str, req: DAOCancelRequest):
        by = resolve_who(req.by)
        ok, msg = dao_manager.cancel(proposal_id, by)
        if not ok:
            raise HTTPException(400, msg)
        p = dao_manager.get(proposal_id)
        peer_manager.broadcast_state_event({"kind": "dao_proposal", "data": p.to_dict()})
        return {"status": "cancelled", "id": proposal_id}

'''
    text, _ = insert_before(text, anchor, insert, marker="# DAO (#13)")

    path.write_text(text, encoding="utf-8")
    log_ok(f"patched: {path.relative_to(ROOT)}")


# =============================================================================
# CLI/MAIN.PY
# =============================================================================

def patch_cli():
    path = ROOT / "cli" / "main.py"
    if not path.exists():
        log_err(f"not found: {path}")
        return
    backup(path)
    text = path.read_text(encoding="utf-8")

    # 1. import
    anchor = "from core.protocols.ai_memory import (\n    AIMemoryManager, KINDS as AI_KINDS, PRIORITIES as AI_PRIORITIES,\n    KIND_EMOJI, PRIORITY_EMOJI,\n)"
    insert = "\nfrom core.governance.dao import DAOManager"
    text, _ = insert_after(text, anchor, insert, marker="from core.governance.dao import")

    # 2. commands before ГЛАВНАЯ
    anchor = '''# =============================================================================
# ГЛАВНАЯ
# ============================================================================='''
    insert = '''# =============================================================================
# DAO (#13)
# =============================================================================

def cmd_dao_stats(a):
    url = _node_url(a)
    d = _node_get(url, "/dao/stats")
    if not d:
        print(f"{Fore.RED}Node {url} not responding"); return 1
    print(f"{Fore.CYAN}DAO -- statistics")
    print(f"   Total:        {Fore.YELLOW}{d['total']}")
    print(f"   Reputation:   {Fore.YELLOW}{d['total_reputation']}")
    print(f"   Quorum:       {d['quorum_percent']}%")
    print(f"   Pass:         >{d['pass_threshold']}%")
    print(f"   Voting:       {d['voting_blocks']} blocks")
    print(f"   Exec delay:   {d['execution_delay_blocks']} blocks")
    if d.get("by_status"):
        print(f"   By status:    {d['by_status']}")
    return 0


def cmd_dao_list(a):
    url = _node_url(a)
    d = _node_get(url, "/dao/all")
    if not d:
        print(f"{Fore.RED}Node {url} not responding"); return 1
    print(f"{Fore.CYAN}DAO -- proposals: {len(d['proposals'])}")
    if not d["proposals"]:
        print(f"   {Fore.YELLOW}No proposals yet"); return 0
    rows = []
    for p in d["proposals"]:
        rows.append([p["id"], p["kind"], p["status"],
                     p["title"][:40],
                     p["author"][:20] + "..."])
    print(tabulate(rows, headers=["ID", "Kind", "Status", "Title", "Author"],
                   tablefmt="rounded_outline"))
    return 0


def cmd_dao_show(a):
    url = _node_url(a)
    d = _node_get(url, f"/dao/{a.proposal_id}")
    if not d:
        print(f"{Fore.RED}Proposal not found"); return 1
    print(f"{Fore.CYAN}DAO {d['id']}")
    print(f"   Kind:      {d['kind']}")
    print(f"   Status:    {Fore.YELLOW}{d['status']}")
    print(f"   Author:    {d['author']}")
    print(f"   Title:     {d['title']}")
    print(f"   Desc:      {d['description'][:80]}")
    yes_w = sum(v["weight"] for v in d["votes"].values() if v["choice"] == "yes")
    no_w = sum(v["weight"] for v in d["votes"].values() if v["choice"] == "no")
    print(f"   Yes/No:    {Fore.GREEN}{yes_w}{Fore.RESET} / {Fore.RED}{no_w}{Fore.RESET}")
    print(f"   Votes:     {len(d['votes'])}")
    print(f"   Voting end: block {d['voting_ends_at_height']}")
    return 0


def cmd_dao_create(a):
    url = _node_url(a)
    if not Wallet.exists(a.author):
        print(f"{Fore.RED}Wallet {a.author} not found"); return 1
    w = Wallet.load(a.author)
    payload = {}
    if a.kind.upper() == "SPEND":
        if not a.contribution:
            print(f"{Fore.RED}SPEND requires --contribution <id>"); return 1
        payload["contribution_id"] = a.contribution
    try:
        r = requests.post(f"{url}/dao/create", json={
            "author": w.address,
            "title": a.title,
            "description": a.description,
            "kind": a.kind.upper(),
            "payload": payload,
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}{r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}{e}"); return 1
    print(f"{Fore.GREEN}Proposal created: {d['id']}")
    print(f"   Title:      {d['title']}")
    print(f"   Voting end: block {d['voting_ends_at_height']}")
    print(f"\\n   Vote: aix dao vote {d['id']} <wallet> yes|no")
    return 0


def cmd_dao_vote(a):
    url = _node_url(a)
    if not Wallet.exists(a.voter):
        print(f"{Fore.RED}Wallet {a.voter} not found"); return 1
    w = Wallet.load(a.voter)
    try:
        r = requests.post(f"{url}/dao/{a.proposal_id}/vote", json={
            "voter": w.address,
            "choice": a.choice,
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}{r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}{e}"); return 1
    print(f"{Fore.GREEN}Vote accepted")
    print(f"   Yes: {d['yes_weight']}, No: {d['no_weight']}, Votes: {d['votes_count']}")
    return 0


def cmd_dao_tally(a):
    url = _node_url(a)
    try:
        r = requests.post(f"{url}/dao/{a.proposal_id}/tally", timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}{r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}{e}"); return 1
    print(f"{Fore.GREEN}Tallied: {d['proposal_status']}")
    print(f"   Yes: {d['yes_weight']}, No: {d['no_weight']}")
    return 0


def cmd_dao_execute(a):
    url = _node_url(a)
    try:
        r = requests.post(f"{url}/dao/{a.proposal_id}/execute", timeout=15)
        if r.status_code != 200:
            print(f"{Fore.RED}{r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}{e}"); return 1
    print(f"{Fore.GREEN}Executed: {d['proposal_status']}")
    if d.get("tx_id"):
        print(f"   TX: {d['tx_id'][:32]}...")
    return 0


'''
    text, _ = insert_before(text, anchor, insert, marker="# DAO (#13)")

    # 3. argparse
    anchor = "    args = p.parse_args()\n    return args.func(args)"
    insert = '''    # DAO (#13)
    pdao = sub.add_parser("dao", help="DAO (#13)")
    pdao.add_argument("--node", default=DEFAULT_NODE)
    dsub = pdao.add_subparsers(dest="dao_cmd", required=True)

    dsub.add_parser("stats", help="Statistics").set_defaults(func=cmd_dao_stats)
    dsub.add_parser("list", help="All proposals").set_defaults(func=cmd_dao_list)

    dsh = dsub.add_parser("show", help="Show proposal")
    dsh.add_argument("proposal_id")
    dsh.set_defaults(func=cmd_dao_show)

    dcr = dsub.add_parser("create", help="Create proposal")
    dcr.add_argument("author", help="Wallet name")
    dcr.add_argument("title")
    dcr.add_argument("description")
    dcr.add_argument("--kind", default="TEXT", choices=["TEXT", "SPEND"])
    dcr.add_argument("--contribution", default=None,
                     help="For SPEND: contribution_id")
    dcr.set_defaults(func=cmd_dao_create)

    dv = dsub.add_parser("vote", help="Vote")
    dv.add_argument("proposal_id")
    dv.add_argument("voter", help="Wallet name")
    dv.add_argument("choice", choices=["yes", "no"])
    dv.set_defaults(func=cmd_dao_vote)

    dt = dsub.add_parser("tally", help="Finalize voting")
    dt.add_argument("proposal_id")
    dt.set_defaults(func=cmd_dao_tally)

    de = dsub.add_parser("execute", help="Execute passed proposal")
    de.add_argument("proposal_id")
    de.set_defaults(func=cmd_dao_execute)

'''
    text, _ = insert_before(text, anchor, insert, marker='pdao = sub.add_parser("dao"')

    path.write_text(text, encoding="utf-8")
    log_ok(f"patched: {path.relative_to(ROOT)}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 50)
    print("  AIX OS - DAO patcher")
    print("=" * 50)

    required = [
        ROOT / "core" / "governance" / "dao.py",
        ROOT / "core" / "protocols" / "sbt.py",
        ROOT / "core" / "protocols" / "poc.py",
    ]
    for f in required:
        if not f.exists():
            log_err(f"missing: {f.relative_to(ROOT)}")
            return 1

    try:
        patch_server()
        patch_cli()
    except Exception as e:
        log_err(f"{e}")
        return 1

    print()
    log_ok("All DAO patches applied.")
    print()
    print("Verify:")
    print("  pytest tests/test_dao.py -v")
    print("  .\\.venv\\Scripts\\python.exe -m network.server --port 8010 --data data/chain_A.json")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())