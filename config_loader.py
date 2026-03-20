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
