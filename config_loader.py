import json
import os

_CONFIG_PATH = os.path.join("data", "config.json")


def _load() -> dict:
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict) -> None:
    os.makedirs("data", exist_ok=True)
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_owner_id() -> int | None:
    val = _load().get("owner_id")
    return int(val) if val else None


def set_owner_id(user_id: int) -> None:
    data = _load()
    data["owner_id"] = user_id
    _save(data)


def get_guild_id() -> str | None:
    val = _load().get("guild_id")
    return str(val) if val else None


def set_guild_id(guild_id: int | str | None) -> None:
    data = _load()
    data["guild_id"] = guild_id
    _save(data)


def get_support_invite() -> str | None:
    return _load().get("support_invite") or None


def set_support_invite(invite_url: str | None) -> None:
    data = _load()
    data["support_invite"] = invite_url
    _save(data)


# ── Noprefix users ────────────────────────────────────────────────────────────

def get_noprefix_users() -> list[int]:
    raw = _load().get("noprefix_users", [])
    return [int(u) for u in raw]


def is_noprefix_user(user_id: int) -> bool:
    return user_id in get_noprefix_users()


def add_noprefix_user(user_id: int) -> None:
    data = _load()
    users = data.get("noprefix_users", [])
    if user_id not in users:
        users.append(user_id)
    data["noprefix_users"] = users
    _save(data)


def remove_noprefix_user(user_id: int) -> None:
    data = _load()
    users = data.get("noprefix_users", [])
    data["noprefix_users"] = [u for u in users if u != user_id]
    _save(data)


def toggle_noprefix_user(user_id: int) -> bool:
    """Toggle noprefix for user. Returns True if added, False if removed."""
    if is_noprefix_user(user_id):
        remove_noprefix_user(user_id)
        return False
    add_noprefix_user(user_id)
    return True
