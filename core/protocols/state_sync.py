"""
AIX OS — State Sync (#16).

Синхронизация состояния протоколов между нодами.

Поддерживает:
- Gift-Link, Time-Lock, SBT, DMS, AIX-ID, Burn, Contacts, Swap, PoC
"""

import json
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.protocols.gift_link import GiftLink
from core.protocols.time_lock import TimeLock
from core.protocols.sbt import Medal
from core.protocols.dead_mans_switch import Inheritance
from core.protocols.aix_id import AIXProfile
from core.protocols.burn_to_mint import BurnArtifact
from core.protocols.contacts import Contact
from core.protocols.poc import Contribution, RewardPool
from core.governance.dao import Proposal


def export_state(gift_manager, timelock_manager, sbt_manager,
                 inheritance_manager=None, id_manager=None,
                 burn_manager=None, contacts_manager=None,
                 swap_manager=None, poc_manager=None, dao_manager=None) -> dict:
    result = {
        "timestamp": time.time(),
        "gifts": [l.to_dict() for l in gift_manager.links.values()],
        "timelocks": [l.to_dict() for l in timelock_manager.locks.values()],
        "medals": [m.to_dict() for m in sbt_manager.medals],
    }
    if inheritance_manager is not None:
        result["inheritances"] = [s.to_dict() for s in inheritance_manager.switches.values()]
    if id_manager is not None:
        result["aix_ids"] = [p.to_dict() for p in id_manager.profiles.values()]
    if burn_manager is not None:
        result["burn_artifacts"] = [a.to_dict() for a in burn_manager.artifacts.values()]
    if contacts_manager is not None:
        result["contacts"] = [c.to_dict() for c in contacts_manager.by_phone.values()]
    if swap_manager is not None:
        result["swap_pools"] = [p.to_dict() for p in swap_manager.pools.values()]
        result["swap_balances"] = swap_manager.balances
    if poc_manager is not None:
        result["poc_contributions"] = [c.to_dict() for c in poc_manager.contributions.values()]
        result["poc_pool"] = poc_manager.pool.to_dict()
    if dao_manager is not None:
        result["dao_proposals"] = dao_manager.export_all()
    return result


def import_state(data: dict, gift_manager, timelock_manager, sbt_manager,
                 inheritance_manager=None, id_manager=None,
                 burn_manager=None, contacts_manager=None,
                 swap_manager=None, poc_manager=None, dao_manager=None) -> dict:
    added = {"gifts": 0, "timelocks": 0, "medals": 0, "inheritances": 0,
             "aix_ids": 0, "burn_artifacts": 0, "contacts": 0, "swap_pools": 0,
             "poc_contributions": 0, "dao_proposals": 0}
    skipped = {"gifts": 0, "timelocks": 0, "medals": 0, "inheritances": 0,
               "aix_ids": 0, "burn_artifacts": 0, "contacts": 0, "swap_pools": 0,
               "poc_contributions": 0, "dao_proposals": 0}

    # Gifts
    for item in data.get("gifts", []):
        try:
            link = GiftLink.from_dict(item)
            existing = gift_manager.links.get(link.code)
            if existing:
                if link.claimed and not existing.claimed:
                    gift_manager.links[link.code] = link
                    added["gifts"] += 1
                elif link.cancelled and not existing.cancelled:
                    gift_manager.links[link.code] = link
                    added["gifts"] += 1
                else:
                    skipped["gifts"] += 1
                continue
            gift_manager.links[link.code] = link
            added["gifts"] += 1
        except Exception as e:
            print(f"WARN: import gift: {e}")

    # TimeLocks
    for item in data.get("timelocks", []):
        try:
            lock = TimeLock.from_dict(item)
            existing = timelock_manager.locks.get(lock.id)
            if existing:
                if lock.released and not existing.released:
                    timelock_manager.locks[lock.id] = lock
                    added["timelocks"] += 1
                elif lock.cancelled and not existing.cancelled:
                    timelock_manager.locks[lock.id] = lock
                    added["timelocks"] += 1
                else:
                    skipped["timelocks"] += 1
                continue
            timelock_manager.locks[lock.id] = lock
            added["timelocks"] += 1
        except Exception as e:
            print(f"WARN: import timelock: {e}")

    # Medals
    existing_keys = {(m.medal_id, m.owner, m.issued_at)
                     for m in sbt_manager.medals}
    for item in data.get("medals", []):
        try:
            medal = Medal.from_dict(item)
            key = (medal.medal_id, medal.owner, medal.issued_at)
            if key in existing_keys:
                for m in sbt_manager.medals:
                    if (m.medal_id, m.owner, m.issued_at) == key:
                        if medal.revoked and not m.revoked:
                            m.revoked = True
                            m.revoked_at = medal.revoked_at
                            m.revoked_reason = medal.revoked_reason
                            added["medals"] += 1
                            break
                else:
                    skipped["medals"] += 1
                continue
            sbt_manager.medals.append(medal)
            existing_keys.add(key)
            added["medals"] += 1
        except Exception as e:
            print(f"WARN: import medal: {e}")

    # Inheritances
    if inheritance_manager is not None:
        for item in data.get("inheritances", []):
            try:
                sw = Inheritance.from_dict(item)
                existing = inheritance_manager.switches.get(sw.id)
                if existing:
                    if (sw.triggered and not existing.triggered) or \
                       (sw.cancelled and not existing.cancelled) or \
                       (sw.last_checkin > existing.last_checkin):
                        inheritance_manager.switches[sw.id] = sw
                        added["inheritances"] += 1
                    else:
                        skipped["inheritances"] += 1
                    continue
                inheritance_manager.switches[sw.id] = sw
                added["inheritances"] += 1
            except Exception as e:
                print(f"WARN: import inheritance: {e}")

    # AIX-IDs
    if id_manager is not None:
        for item in data.get("aix_ids", []):
            try:
                ok, msg = id_manager.import_profile(item)
                if ok and msg in ("добавлен", "обновлён"):
                    added["aix_ids"] += 1
                else:
                    skipped["aix_ids"] += 1
            except Exception as e:
                print(f"WARN: import aix_id: {e}")

    # Burn Artifacts
    if burn_manager is not None:
        for item in data.get("burn_artifacts", []):
            try:
                ok, msg = burn_manager.import_artifact(item)
                if ok and msg == "добавлен":
                    added["burn_artifacts"] += 1
                else:
                    skipped["burn_artifacts"] += 1
            except Exception as e:
                print(f"WARN: import burn_artifact: {e}")

    # Contacts
    if contacts_manager is not None:
        for item in data.get("contacts", []):
            try:
                ok, msg = contacts_manager.import_contact(item)
                if ok and msg in ("добавлен", "обновлён"):
                    added["contacts"] += 1
                else:
                    skipped["contacts"] += 1
            except Exception as e:
                print(f"WARN: import contact: {e}")

    # Swap Pools + Balances
    if swap_manager is not None:
        swap_data = {
            "pools": data.get("swap_pools", []),
            "balances": data.get("swap_balances", {}),
        }
        if swap_data["pools"] or swap_data["balances"]:
            try:
                swap_manager.import_state(swap_data)
                added["swap_pools"] = len(swap_data["pools"])
            except Exception as e:
                print(f"WARN: import swap: {e}")

    # PoC
    if poc_manager is not None:
        for item in data.get("poc_contributions", []):
            try:
                ok, msg = poc_manager.import_contribution(item)
                if ok and msg in ("добавлен", "обновлён"):
                    added["poc_contributions"] += 1
                else:
                    skipped["poc_contributions"] += 1
            except Exception as e:
                print(f"WARN: import poc_contribution: {e}")
        if "poc_pool" in data:
            try:
                poc_manager.import_pool(data["poc_pool"])
            except Exception as e:
                print(f"WARN: import poc_pool: {e}")

    # DAO
    if dao_manager is not None:
        for item in data.get("dao_proposals", []):
            try:
                ok, msg = dao_manager.import_proposal(item)
                if ok and msg in ("добавлен", "обновлён", "голоса обновлены"):
                    added["dao_proposals"] += 1
                else:
                    skipped["dao_proposals"] += 1
            except Exception as e:
                print(f"WARN: import dao_proposal: {e}")

    # Save
    if added["gifts"] > 0:
        gift_manager._save()
    if added["timelocks"] > 0:
        timelock_manager._save()
    if added["medals"] > 0:
        sbt_manager._save()
    if inheritance_manager and added["inheritances"] > 0:
        inheritance_manager._save()
    if id_manager and added["aix_ids"] > 0:
        id_manager._save()
    if burn_manager and added["burn_artifacts"] > 0:
        burn_manager._save()
    if contacts_manager and added["contacts"] > 0:
        contacts_manager._save()

    return {"added": added, "skipped": skipped}


# =============================================================================
# СОБЫТИЯ
# =============================================================================

def make_gift_event(link: GiftLink) -> dict:
    return {"kind": "gift", "data": link.to_dict()}


def make_timelock_event(lock: TimeLock) -> dict:
    return {"kind": "timelock", "data": lock.to_dict()}


def make_medal_event(medal: Medal) -> dict:
    return {"kind": "medal", "data": medal.to_dict()}


def make_inheritance_event(sw: Inheritance) -> dict:
    return {"kind": "inheritance", "data": sw.to_dict()}


def make_id_event(profile: AIXProfile) -> dict:
    return {"kind": "aix_id", "data": profile.to_dict()}


def make_burn_event(artifact: BurnArtifact) -> dict:
    return {"kind": "burn_artifact", "data": artifact.to_dict()}


def make_contact_event(contact: Contact) -> dict:
    return {"kind": "contact", "data": contact.to_dict()}


def make_swap_event(pool) -> dict:
    return {"kind": "swap_pool", "data": pool.to_dict()}


def make_poc_event(contribution: Contribution) -> dict:
    return {"kind": "poc_contribution", "data": contribution.to_dict()}


def make_poc_pool_event(pool: RewardPool) -> dict:
    return {"kind": "poc_pool", "data": pool.to_dict()}


def make_dao_event(proposal: Proposal) -> dict:
    return {"kind": "dao_proposal", "data": proposal.to_dict()}


def apply_event(event: dict, gift_manager, timelock_manager, sbt_manager,
                inheritance_manager=None, id_manager=None,
                burn_manager=None, contacts_manager=None,
                swap_manager=None, poc_manager=None, dao_manager=None) -> tuple:
    kind = event.get("kind")
    data = event.get("data", {})

    try:
        if kind == "gift":
            link = GiftLink.from_dict(data)
            existing = gift_manager.links.get(link.code)
            if existing and (link.claimed or link.cancelled):
                gift_manager.links[link.code] = link
                gift_manager._save()
                return True, f"gift {link.code} обновлён"
            if existing:
                return True, f"gift {link.code} уже есть"
            gift_manager.links[link.code] = link
            gift_manager._save()
            return True, f"gift {link.code} добавлен"

        if kind == "timelock":
            lock = TimeLock.from_dict(data)
            existing = timelock_manager.locks.get(lock.id)
            if existing and (lock.released or lock.cancelled):
                timelock_manager.locks[lock.id] = lock
                timelock_manager._save()
                return True, f"timelock {lock.id} обновлён"
            if existing:
                return True, f"timelock {lock.id} уже есть"
            timelock_manager.locks[lock.id] = lock
            timelock_manager._save()
            return True, f"timelock {lock.id} добавлен"

        if kind == "medal":
            medal = Medal.from_dict(data)
            key = (medal.medal_id, medal.owner, medal.issued_at)
            for m in sbt_manager.medals:
                if (m.medal_id, m.owner, m.issued_at) == key:
                    if medal.revoked and not m.revoked:
                        m.revoked = True
                        m.revoked_at = medal.revoked_at
                        m.revoked_reason = medal.revoked_reason
                        sbt_manager._save()
                        return True, f"медаль {medal.medal_id} отозвана"
                    return True, f"медаль {medal.medal_id} уже есть"
            sbt_manager.medals.append(medal)
            sbt_manager._save()
            return True, f"медаль {medal.medal_id} добавлена"

        if kind == "inheritance":
            if inheritance_manager is None:
                return False, "inheritance manager недоступен"
            sw = Inheritance.from_dict(data)
            existing = inheritance_manager.switches.get(sw.id)
            if existing:
                if (sw.triggered and not existing.triggered) or \
                   (sw.cancelled and not existing.cancelled) or \
                   (sw.last_checkin > existing.last_checkin):
                    inheritance_manager.switches[sw.id] = sw
                    inheritance_manager._save()
                    return True, f"inheritance {sw.id} обновлён"
                return True, f"inheritance {sw.id} уже есть"
            inheritance_manager.switches[sw.id] = sw
            inheritance_manager._save()
            return True, f"inheritance {sw.id} добавлен"

        if kind == "aix_id":
            if id_manager is None:
                return False, "id manager недоступен"
            ok, msg = id_manager.import_profile(data)
            return ok, f"aix_id: {msg}"

        if kind == "burn_artifact":
            if burn_manager is None:
                return False, "burn manager недоступен"
            ok, msg = burn_manager.import_artifact(data)
            return ok, f"burn_artifact: {msg}"

        if kind == "contact":
            if contacts_manager is None:
                return False, "contacts manager недоступен"
            ok, msg = contacts_manager.import_contact(data)
            return ok, f"contact: {msg}"

        if kind == "swap_pool":
            if swap_manager is None:
                return False, "swap manager недоступен"
            from core.protocols.swap import SwapPool
            pool = SwapPool.from_dict(data)
            existing = swap_manager.pools.get(pool.id)
            if existing is None:
                swap_manager.pools[pool.id] = pool
                swap_manager._save()
                return True, f"swap_pool {pool.id} добавлен"
            if (pool.reserve_a + pool.reserve_b) > (existing.reserve_a + existing.reserve_b):
                swap_manager.pools[pool.id] = pool
                swap_manager._save()
                return True, f"swap_pool {pool.id} обновлён"
            return True, f"swap_pool {pool.id} уже актуален"

        if kind == "poc_contribution":
            if poc_manager is None:
                return False, "poc manager недоступен"
            ok, msg = poc_manager.import_contribution(data)
            return ok, f"poc_contribution: {msg}"

        if kind == "poc_pool":
            if poc_manager is None:
                return False, "poc manager недоступен"
            ok, msg = poc_manager.import_pool(data)
            return ok, f"poc_pool: {msg}"

        if kind == "dao_proposal":
            if dao_manager is None:
                return False, "dao manager недоступен"
            ok, msg = dao_manager.import_proposal(data)
            return ok, f"dao_proposal: {msg}"

        return False, f"неизвестный kind: {kind}"
    except Exception as e:
        return False, f"ошибка применения: {e}"