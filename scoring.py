import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Optional

SUSPICIOUS_PATTERNS = [
    r"^\w{1,4}\d{4,}$",
    r"^[a-z]+\d{3,}[a-z]*$",
    r"^(user|alt|fake|acc|acct)\d*$",
    r"^[a-z]{2,5}[._-]\d{4,}$",
    r"^[a-z]{6,}[0-9]{3,}$",
    r"^[a-zA-Z0-9]{18,}$",
]

def _username_risk(username: str) -> tuple[int, list[str]]:
    score = 0
    reasons = []
    clean = username.lower().replace("_", "").replace(".", "").replace("-", "")
    digit_ratio = sum(c.isdigit() for c in clean) / max(len(clean), 1)

    if digit_ratio > 0.45:
        score += 14
        reasons.append("High digit ratio in username")
    elif digit_ratio > 0.3:
        score += 7

    for pattern in SUSPICIOUS_PATTERNS:
        if re.match(pattern, username, re.IGNORECASE):
            score += 12
            reasons.append("Suspicious username pattern detected")
            break

    if len(username) < 4:
        score += 6
        reasons.append("Unusually short username")

    random_score = _randomness_score(clean)
    if random_score > 0.72:
        score += 10
        reasons.append("Username appears algorithmically generated")

    return min(score, 25), reasons

def _randomness_score(text: str) -> float:
    if len(text) < 4:
        return 0.0
    unique = len(set(text)) / len(text)
    vowels = sum(c in "aeiou" for c in text) / max(len(text), 1)
    return round((unique * 0.6 + (1 - vowels) * 0.4), 3)

def _account_age_risk(created_at: datetime) -> tuple[int, list[str]]:
    now = datetime.now(timezone.utc)
    age_days = (now - created_at).days
    score = 0
    reasons = []

    if age_days < 3:
        score = 32
        reasons.append(f"Account created {age_days}d ago — very new")
    elif age_days < 14:
        score = 24
        reasons.append(f"Account created {age_days}d ago — newly created")
    elif age_days < 30:
        score = 16
        reasons.append(f"Account created {age_days}d ago — recently created")
    elif age_days < 90:
        score = 8
        reasons.append(f"Account is {age_days}d old — relatively new")
    elif age_days < 180:
        score = 4

    return score, reasons

def _cluster_risk(
    member_id: int, guild_id: int, created_at: datetime, history: list[dict]
) -> tuple[int, list[str]]:
    score = 0
    reasons = []
    if not history:
        return 0, []

    now_ts = datetime.now(timezone.utc).timestamp()
    recent = []
    for entry in history[-50:]:
        if str(entry.get("user_id")) == str(member_id):
            continue
        try:
            joined = datetime.fromisoformat(entry["joined_at"])
            diff = abs(now_ts - joined.timestamp())
            if diff < 600:
                recent.append(("10min", entry))
            elif diff < 3600:
                recent.append(("1hr", entry))
            elif diff < 86400:
                recent.append(("24hr", entry))
        except Exception:
            continue

    ten_min = [e for label, e in recent if label == "10min"]
    one_hr = [e for label, e in recent if label == "1hr"]

    if len(ten_min) >= 3:
        score = 26
        reasons.append(f"Join cluster anomaly — {len(ten_min)+1} users joined within 10 min")
    elif len(ten_min) >= 2:
        score = 16
        reasons.append(f"Possible join cluster — {len(ten_min)+1} users joined recently")
    elif len(one_hr) >= 4:
        score = 10
        reasons.append("Elevated join activity detected in this hour")

    return score, reasons

def _similarity_risk(
    username: str, created_at: datetime, history: list[dict]
) -> tuple[int, list[str]]:
    score = 0
    reasons = []
    if not history:
        return 0, []

    age_days = (datetime.now(timezone.utc) - created_at).days
    similar_users = 0
    similar_age_users = 0

    for entry in history[-50:]:
        e_name = entry.get("username", "")
        ratio = SequenceMatcher(None, username.lower(), e_name.lower()).ratio()
        if ratio > 0.78 and e_name.lower() != username.lower():
            similar_users += 1

        try:
            e_created = datetime.fromisoformat(entry.get("account_created", ""))
            e_age = (datetime.now(timezone.utc) - e_created).days
            if abs(e_age - age_days) <= 7 and age_days < 30:
                similar_age_users += 1
        except Exception:
            pass

    if similar_users >= 2:
        score += 18
        reasons.append(f"Behavioral similarity observed ({similar_users} similar usernames)")
    elif similar_users == 1:
        score += 9
        reasons.append("Pattern match detected with recent user")

    if similar_age_users >= 2 and age_days < 30:
        score += 10
        reasons.append(f"Multiple new accounts with similar creation window")
    elif similar_age_users == 1 and age_days < 14:
        score += 5

    return min(score, 25), reasons

def calculate_risk(member, guild_history: list[dict]) -> dict:
    score = 0
    all_reasons = []
    breakdown = {"static": 0, "behavioral": 0, "cluster": 0}

    age_score, age_reasons = _account_age_risk(member.created_at)
    user_score, user_reasons = _username_risk(member.name)
    cluster_score, cluster_reasons = _cluster_risk(
        member.id, member.guild.id, member.created_at, guild_history
    )
    sim_score, sim_reasons = _similarity_risk(
        member.name, member.created_at, guild_history
    )

    breakdown["static"] = age_score + user_score
    breakdown["behavioral"] = sim_score
    breakdown["cluster"] = cluster_score

    score = min(100, breakdown["static"] + breakdown["behavioral"] + breakdown["cluster"])
    all_reasons = age_reasons + user_reasons + cluster_reasons + sim_reasons

    if score >= 70:
        classification = "HIGH"
    elif score >= 40:
        classification = "MEDIUM"
    else:
        classification = "LOW"

    age_days = (datetime.now(timezone.utc) - member.created_at).days

    return {
        "score": score,
        "classification": classification,
        "reasons": all_reasons[:5],
        "breakdown": breakdown,
        "details": {
            "account_age_days": age_days,
            "username": member.name,
            "display_name": member.display_name,
        },
    }

def explain_score(result: dict) -> str:
    score = result["score"]
    cls = result["classification"]
    bd = result["breakdown"]
    reasons = result["reasons"]

    lines = [
        f"**Score: {score}/100 — {cls} Risk**\n",
        "**Score breakdown:**",
        f"  · Static signals: `{bd['static']}pts` — account age, username structure",
        f"  · Behavioral: `{bd['behavioral']}pts` — similarity to recent members",
        f"  · Cluster detection: `{bd['cluster']}pts` — join timing analysis",
        "",
        "**Key signals identified:**",
    ]
    for r in reasons:
        lines.append(f"  · {r}")

    if not reasons:
        lines.append("  · No notable risk indicators found")

    lines += [
        "",
        "*Scores are probabilistic — not definitive. This is a risk indicator, not a verdict.*",
    ]
    return "\n".join(lines)
