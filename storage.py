import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

STORAGE_FILE = "data/user_history.json"

def _load() -> dict:
    if not os.path.exists(STORAGE_FILE):
        return {}
    with open(STORAGE_FILE, "r") as f:
        return json.load(f)

def _save(data: dict) -> None:
    os.makedirs(os.path.dirname(STORAGE_FILE), exist_ok=True)
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def _d(data: dict, *keys, default=None):
    for k in keys:
        data.setdefault(k, default() if callable(default) else default)
    return data

# ── Join / Scan ──────────────────────────────────────────────────────────────

def record_join(member_id: int, username: str, guild_id: int, created_at: datetime) -> None:
    data = _load()
    history = data.setdefault("join_history", [])
    history.append({
        "user_id": str(member_id),
        "username": username,
        "guild_id": str(guild_id),
        "joined_at": datetime.now(timezone.utc).isoformat(),
        "account_created": created_at.isoformat(),
    })
    data["join_history"] = history[-500:]
    _save(data)

def get_guild_history(guild_id: int) -> list:
    data = _load()
    gid = str(guild_id)
    return [e for e in data.get("join_history", []) if e.get("guild_id") == gid]

def save_scan_result(user_id: int, guild_id: int, result: dict) -> None:
    data = _load()
    data.setdefault("scan_history", {})[f"{guild_id}:{user_id}"] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }
    _save(data)

def get_scan_result(user_id: int, guild_id: int) -> Optional[dict]:
    data = _load()
    return data.get("scan_history", {}).get(f"{guild_id}:{user_id}")

# ── Warnings ─────────────────────────────────────────────────────────────────

def add_warning(user_id: int, guild_id: int, reason: str, moderator_id: int) -> dict:
    data = _load()
    key = f"{guild_id}:{user_id}"
    warns = data.setdefault("warnings", {}).setdefault(key, [])
    entry = {
        "id": str(uuid.uuid4())[:8].upper(),
        "reason": reason,
        "moderator_id": str(moderator_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    warns.append(entry)
    _save(data)
    return entry

def get_warnings(user_id: int, guild_id: int) -> list:
    data = _load()
    return data.get("warnings", {}).get(f"{guild_id}:{user_id}", [])

def remove_warning(user_id: int, guild_id: int, warn_id: str) -> bool:
    data = _load()
    key = f"{guild_id}:{user_id}"
    warns = data.get("warnings", {}).get(key, [])
    new_warns = [w for w in warns if w["id"] != warn_id.upper()]
    if len(new_warns) == len(warns):
        return False
    data.setdefault("warnings", {})[key] = new_warns
    _save(data)
    return True

def clear_warnings(user_id: int, guild_id: int) -> int:
    data = _load()
    key = f"{guild_id}:{user_id}"
    count = len(data.get("warnings", {}).get(key, []))
    data.setdefault("warnings", {})[key] = []
    _save(data)
    return count

# ── Notes ─────────────────────────────────────────────────────────────────────

def add_note(user_id: int, guild_id: int, note: str, author_id: int) -> dict:
    data = _load()
    key = f"{guild_id}:{user_id}"
    notes = data.setdefault("notes", {}).setdefault(key, [])
    entry = {
        "id": str(uuid.uuid4())[:8].upper(),
        "note": note,
        "author_id": str(author_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    notes.append(entry)
    _save(data)
    return entry

def get_notes(user_id: int, guild_id: int) -> list:
    data = _load()
    return data.get("notes", {}).get(f"{guild_id}:{user_id}", [])

def remove_note(user_id: int, guild_id: int, note_id: str) -> bool:
    data = _load()
    key = f"{guild_id}:{user_id}"
    notes = data.get("notes", {}).get(key, [])
    new_notes = [n for n in notes if n["id"] != note_id.upper()]
    if len(new_notes) == len(notes):
        return False
    data.setdefault("notes", {})[key] = new_notes
    _save(data)
    return True

# ── Flags ─────────────────────────────────────────────────────────────────────

def flag_user(user_id: int, guild_id: int, reason: str, flagged_by: int) -> None:
    data = _load()
    data.setdefault("flags", {}).setdefault(str(guild_id), {})[str(user_id)] = {
        "reason": reason,
        "flagged_by": str(flagged_by),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _save(data)

def unflag_user(user_id: int, guild_id: int) -> bool:
    data = _load()
    gflags = data.get("flags", {}).get(str(guild_id), {})
    if str(user_id) not in gflags:
        return False
    del gflags[str(user_id)]
    _save(data)
    return True

def get_flag(user_id: int, guild_id: int) -> Optional[dict]:
    data = _load()
    return data.get("flags", {}).get(str(guild_id), {}).get(str(user_id))

def get_all_flags(guild_id: int) -> dict:
    data = _load()
    return data.get("flags", {}).get(str(guild_id), {})

# ── Server Config ─────────────────────────────────────────────────────────────

_CONFIG_DEFAULTS = {
    "mod_log_channel": None,
    "alerts_channel": None,
    "autorole": None,
    "antispam": False,
    "antilink": False,
    "capsfilter": False,
    "risk_alerts": False,
    "activity_alerts": False,
    "spam_alerts": False,
    "autokick_days": None,
    "autowarn_spam": False,
}

def get_server_config(guild_id: int) -> dict:
    data = _load()
    cfg = data.get("server_config", {}).get(str(guild_id), {})
    return {**_CONFIG_DEFAULTS, **cfg}

def set_server_config(guild_id: int, **kwargs) -> dict:
    data = _load()
    cfg = data.setdefault("server_config", {}).setdefault(str(guild_id), {})
    cfg.update(kwargs)
    _save(data)
    return {**_CONFIG_DEFAULTS, **cfg}

# ── Message Activity ──────────────────────────────────────────────────────────

def record_message(user_id: int, guild_id: int, channel_id: int) -> None:
    data = _load()
    key = f"{guild_id}:{user_id}"
    act = data.setdefault("message_activity", {}).setdefault(key, {
        "total": 0, "last_seen": None, "channels": {}
    })
    act["total"] += 1
    act["last_seen"] = datetime.now(timezone.utc).isoformat()
    ch = str(channel_id)
    act["channels"][ch] = act["channels"].get(ch, 0) + 1
    _save(data)

def get_user_activity(user_id: int, guild_id: int) -> dict:
    data = _load()
    return data.get("message_activity", {}).get(
        f"{guild_id}:{user_id}", {"total": 0, "last_seen": None, "channels": {}}
    )

def get_top_users(guild_id: int, limit: int = 10) -> list[tuple[str, dict]]:
    data = _load()
    prefix = f"{guild_id}:"
    users = [
        (k.split(":", 1)[1], v)
        for k, v in data.get("message_activity", {}).items()
        if k.startswith(prefix)
    ]
    users.sort(key=lambda x: x[1]["total"], reverse=True)
    return users[:limit]

def get_mod_history(user_id: int, guild_id: int) -> list:
    data = _load()
    key = f"{guild_id}:{user_id}"
    history = data.get("mod_history", {}).get(key, [])
    return history

def add_mod_action(user_id: int, guild_id: int, action: str, reason: str, moderator_id: int) -> None:
    data = _load()
    key = f"{guild_id}:{user_id}"
    actions = data.setdefault("mod_history", {}).setdefault(key, [])
    actions.append({
        "action": action,
        "reason": reason,
        "moderator_id": str(moderator_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    data["mod_history"][key] = actions[-50:]
    _save(data)
