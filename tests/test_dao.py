"""AIX OS — тесты DAO (#13)."""
import pytest
from pathlib import Path

from core.protocols.sbt import SBTManager
from core.governance.dao import DAOManager, QUORUM_PERCENT


ALICE = "AIXTA5WAvDBAifiZuYfwfxM57Ajn8kGcG6xj2"
BOB = "AIXTDTWaRqhPzdfmGSgp66G1vg9Rtma1k5WKC"
CAROL = "AIXTXkTCmPUzxkdjdB8eYvga9P7WKG8gTFArM"


@pytest.fixture
def dao(tmp_path):
    sbt = SBTManager(tmp_path / "sbt.json")
    sbt.award("FOUNDER", ALICE, ALICE, "founder")
    sbt.award("EARLY_BIRD", BOB, ALICE, "early")
    sbt.award("EARLY_BIRD", CAROL, ALICE, "early")
    mgr = DAOManager(tmp_path / "dao.json", sbt_manager=sbt)
    return mgr


def test_empty(dao):
    assert len(dao) == 0
    assert dao.stats()["total"] == 0


def test_create_requires_sbt(dao):
    ok, msg = dao.create_proposal(
        author="AIXunknown000000000000000000000000000",
        title="Test proposal",
        description="x",
    )
    assert not ok
    assert "SBT" in msg


def test_create_ok(dao):
    ok, pid = dao.create_proposal(ALICE, "Test proposal", "description")
    assert ok
    assert pid.startswith("DAO-")
    assert len(dao) == 1


def test_title_too_short(dao):
    ok, msg = dao.create_proposal(ALICE, "x", "desc")
    assert not ok
    assert "Title" in msg


def test_vote_requires_sbt(dao):
    ok, pid = dao.create_proposal(ALICE, "Test title", "desc")
    ok, msg = dao.vote(pid, "AIXunknown000000000000000000000000000", "yes")
    assert not ok


def test_vote_yes_no(dao):
    ok, pid = dao.create_proposal(ALICE, "Test title", "desc")
    ok, msg = dao.vote(pid, BOB, "yes")
    assert ok
    p = dao.get(pid)
    assert p.yes_weight() == 10

    ok, msg = dao.vote(pid, CAROL, "no")
    assert ok
    assert p.no_weight() == 10


def test_vote_twice_forbidden(dao):
    ok, pid = dao.create_proposal(ALICE, "Test title", "desc")
    dao.vote(pid, BOB, "yes")
    ok, msg = dao.vote(pid, BOB, "no")
    assert not ok
    assert "уже голосовали" in msg.lower()


def test_tally_quorum_ok(dao):
    ok, pid = dao.create_proposal(ALICE, "Test title", "desc")
    dao.vote(pid, ALICE, "yes")   # weight 50
    dao.vote(pid, BOB, "yes")     # weight 10
    # total_rep = 50+10+10 = 70. voted = 60. 60/70 = 85% >= 30% ✓
    # Move height past voting end
    dao.blockchain = type("BC", (), {"height": lambda self: 999})()
    ok, status = dao.tally(pid)
    assert ok
    assert status == "passed"


def test_tally_quorum_fail(dao):
    ok, pid = dao.create_proposal(ALICE, "Test title", "desc")
    dao.vote(pid, BOB, "yes")   # only weight 10
    # total_rep = 70. voted = 10. 10/70 = 14% < 30% ✗
    dao.blockchain = type("BC", (), {"height": lambda self: 999})()
    ok, status = dao.tally(pid)
    assert ok
    assert status == "rejected"


def test_cancel_only_author(dao):
    ok, pid = dao.create_proposal(ALICE, "Test title", "desc")
    ok, msg = dao.cancel(pid, BOB)
    assert not ok
    ok, msg = dao.cancel(pid, ALICE)
    assert ok


def test_export_import(dao):
    dao.create_proposal(ALICE, "Test title", "desc")
    exported = dao.export_all()
    assert len(exported) == 1

    sbt2 = SBTManager(Path(dao.storage_path).parent / "sbt2.json")
    dao2 = DAOManager(Path(dao.storage_path).parent / "dao2.json", sbt_manager=sbt2)
    ok, msg = dao2.import_proposal(exported[0])
    assert ok
    assert len(dao2) == 1