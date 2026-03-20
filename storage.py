import json
import os
from datetime import datetime, timezone
from typing import Optional

STORAGE_FILE = "data/user_history.json"

def _load() -> dict:
    if not os.path.exists(STORAGE_FILE):
        return {"join_history": [], "scan_history": {}}
    with open(STORAGE_FILE, "r") as f:
        return json.load(f)

def _save(data: dict) -> None:
    os.makedirs(os.path.dirname(STORAGE_FILE), exist_ok=True)
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def record_join(member_id: int, username: str, guild_id: int, created_at: datetime) -> None:
    data = _load()
    entry = {
        "user_id": str(member_id),
        "username": username,
        "guild_id": str(guild_id),
        "joined_at": datetime.now(timezone.utc).isoformat(),
        "account_created": created_at.isoformat(),
    }
    history = data.get("join_history", [])
    history.append(entry)
    data["join_history"] = history[-500:]
    _save(data)

def get_guild_history(guild_id: int) -> list[dict]:
    data = _load()
    gid = str(guild_id)
    return [e for e in data.get("join_history", []) if e.get("guild_id") == gid]

def save_scan_result(user_id: int, guild_id: int, result: dict) -> None:
    data = _load()
    key = f"{guild_id}:{user_id}"
    scans = data.get("scan_history", {})
    scans[key] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }
    data["scan_history"] = scans
    _save(data)

def get_scan_result(user_id: int, guild_id: int) -> Optional[dict]:
    data = _load()
    key = f"{guild_id}:{user_id}"
    return data.get("scan_history", {}).get(key)
