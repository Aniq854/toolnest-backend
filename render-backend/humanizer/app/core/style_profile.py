"""
STYLE PROFILE — "meri awaaz mein likho" feature ka dil.

Do hisson se banta hai:
  1. fingerprint  -> maths se naapi gayi habits (free, koi LLM nahi)
  2. traits       -> LLM se nikale gaye qualitative traits (ek dafa, phir save)

Ek dafa ban kar JSON file mein save ho jata hai, phir har rewrite mein
dobara istemal hota hai — yani LLM cost sirf PEHLI dafa aati hai.
"""
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from app.core import fingerprint as fp
from app.core.prompts import EXTRACT_SYSTEM, build_extract_prompt
from app.providers import get_provider

PROFILE_DIR = Path(__file__).resolve().parents[2] / "data" / "profiles"
MIN_SAMPLE_WORDS = 150

EMPTY_TRAITS = {
    "voice_summary": "",
    "tone_labels": [],
    "signature_phrases": [],
    "common_openers": [],
    "avoid_words": [],
    "punctuation_habits": "",
    "person": "mixed",
    "formality": "neutral",
}


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:48] or "profile"


def _parse_json(raw: str) -> dict:
    """LLM kabhi ```json fence laga deta hai ya aage peeche baatein likh deta hai."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            text = text[start : end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return dict(EMPTY_TRAITS)
    return data if isinstance(data, dict) else dict(EMPTY_TRAITS)


def _clean_traits(data: dict) -> dict:
    out = dict(EMPTY_TRAITS)
    for key, default in EMPTY_TRAITS.items():
        val = data.get(key, default)
        if isinstance(default, list):
            if isinstance(val, str):
                val = [v.strip() for v in val.split(",") if v.strip()]
            out[key] = [str(v).strip() for v in (val or [])][:12]
        else:
            out[key] = str(val or default).strip()[:600]
    return out


async def build_profile(
    name: str,
    samples: list[str],
    provider_name: str | None = None,
) -> dict:
    """
    User ke 2-5 writing samples -> ek mukammal style profile.
    Sirf EK LLM call hoti hai, aur woh bhi sirf profile banate waqt.
    """
    joined = "\n\n---\n\n".join(s.strip() for s in samples if s.strip())
    word_count = len(re.findall(r"[A-Za-z'’]+", joined))

    if word_count < MIN_SAMPLE_WORDS:
        raise ValueError(
            f"Samples bohat chhote hain ({word_count} lafz). Kam az kam "
            f"{MIN_SAMPLE_WORDS} lafz chahiye — 2-3 paragraphs jo AAP ne "
            f"khud likhe hon."
        )

    prints = fp.fingerprint(joined)

    provider = get_provider(provider_name)
    raw = await provider.complete(
        EXTRACT_SYSTEM, build_extract_prompt(joined), temperature=0.3
    )
    traits = _clean_traits(_parse_json(raw))

    return {
        "id": slugify(name),
        "name": name.strip()[:80],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sample_word_count": word_count,
        "fingerprint": prints,
        "traits": traits,
    }


# ----------------------------------------------------------------------
# Storage — JSON files. Koi database nahi, is liye setup zero aur cost zero.
# Baad mein SQLite ya Postgres par shift karna ho to sirf yeh 4 functions
# badalni hongi, baaqi app ko farq nahi padega.
# ----------------------------------------------------------------------


def _path(profile_id: str) -> Path:
    return PROFILE_DIR / f"{slugify(profile_id)}.json"


def save_profile(profile: dict) -> dict:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    _path(profile["id"]).write_text(
        json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return profile


def load_profile(profile_id: str) -> dict | None:
    p = _path(profile_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def list_profiles() -> list[dict]:
    if not PROFILE_DIR.exists():
        return []
    out = []
    for f in sorted(PROFILE_DIR.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        out.append(
            {
                "id": d.get("id", f.stem),
                "name": d.get("name", f.stem),
                "created_at": d.get("created_at", ""),
                "sample_word_count": d.get("sample_word_count", 0),
                "voice_summary": d.get("traits", {}).get("voice_summary", ""),
            }
        )
    return out


def delete_profile(profile_id: str) -> bool:
    p = _path(profile_id)
    if p.exists():
        p.unlink()
        return True
    return False
