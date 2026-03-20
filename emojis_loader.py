import json

_cache: dict | None = None


def _load() -> dict:
    global _cache
    if _cache is None:
        try:
            with open("emojis.json", encoding="utf-8") as f:
                _cache = json.load(f)
        except Exception:
            _cache = {}
    return _cache


def get(name: str, fallback: str = "") -> str:
    return _load().get(name, fallback)


def reload():
    global _cache
    _cache = None
    return _load()
