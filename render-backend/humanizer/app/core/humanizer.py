"""
Poore process ka orchestrator:
  chunk -> prompt banao (profile ke saath) -> LLM -> saaf karo -> jorho
        -> metrics + voice match nikalo
"""
import asyncio
import re

from app.config import settings
from app.core import fingerprint as fp
from app.core import postprocess, prompts, readability, style_profile
from app.core.chunker import chunk_text
from app.providers import get_provider

TEMPERATURE_BY_STRENGTH = {1: 0.4, 2: 0.6, 3: 0.75}


# Aam English function words. Har asli English paragraph mein yeh khoob
# hote hain; Roman Urdu ya kisi doosri zubaan mein qareeb qareeb ghayab.
_EN_STOPWORDS = {
    "the", "and", "is", "are", "of", "to", "in", "that", "it", "for",
    "with", "as", "was", "were", "this", "which", "on", "by", "an", "be",
    "has", "have", "from", "not", "but", "they", "their", "or", "at", "we",
}


def _english_density(text: str) -> float:
    """Per 100 lafz mein kitne English function words hain."""
    words = re.findall(r"[A-Za-z']+", text.lower())
    if not words:
        return 0.0
    hits = sum(1 for w in words if w in _EN_STOPWORDS)
    return 100.0 * hits / len(words)


def language_changed(source: str, output: str) -> bool:
    """
    Kya LLM ne zubaan badal di?

    Yeh ek asli bug se aaya hai: English draft daala, output Roman Urdu
    mein aaya (kyunki system prompt Roman Urdu mein hai). Guard yeh pakadta
    hai — 100% pukhta nahi, magar sab se aam surat pakad leta hai.
    """
    src = _english_density(source)
    out = _english_density(output)
    # Source saaf English tha, magar output se English function words ghayab
    return src >= 8.0 and out < src * 0.45


def needs_repair(before: dict, after: dict) -> bool:
    """
    Kya rewrite ne text ULTA kharab kar diya?

    Yeh sab se ahem quality guard hai. LLM aksar draft ko "zyada formal"
    bana kar bhaari kar deta hai — jo behtar nahi, bad-tar hai. Aisi surat
    mein hum ek doosra (repair) pass chalate hain.
    """
    return (
        after["naturalness_score"] < before["naturalness_score"] - 5  # only repair if clearly worse
        or after["bureaucracy_hits"] > before["bureaucracy_hits"] + 1  # allow 1 slip
        or after["words"] > before["words"] * 1.20  # allow 20% growth
    )


async def humanize(
    text: str,
    tone: str = "blog",
    reading_level: str = "medium",
    strength: int = 2,
    keep_length: bool = True,
    provider_name: str | None = None,
    profile_id: str | None = None,
) -> dict:
    if len(text) > settings.max_input_chars:
        raise ValueError(
            f"Text bohat lamba hai ({len(text)} chars). "
            f"Limit {settings.max_input_chars} hai."
        )

    profile = None
    if profile_id:
        profile = style_profile.load_profile(profile_id)
        if profile is None:
            raise ValueError(f"Style profile '{profile_id}' nahi mila.")

    provider = get_provider(provider_name)
    chunks = chunk_text(text, settings.chunk_size)
    temp = TEMPERATURE_BY_STRENGTH.get(strength, 0.85)

    async def run_chunk(ch: str) -> str:
        user = prompts.build_user_prompt(
            ch, tone, reading_level, strength, keep_length, profile=profile
        )
        raw = await provider.complete(prompts.SYSTEM, user, temperature=temp)
        return postprocess.clean(raw)

    # chunks parallel mein — tez, magar free-tier rate limit ke liye
    # ek waqt mein 3 se zyada nahi
    sem = asyncio.Semaphore(3)

    async def guarded(ch: str) -> str:
        async with sem:
            return await run_chunk(ch)

    rewritten = await asyncio.gather(*(guarded(c) for c in chunks))
    output = "\n\n".join(rewritten).strip()

    before = readability.analyze(text)
    after = readability.analyze(output)

    notes = []
    repair_used = False

    # === LANGUAGE GUARD ===
    # Zubaan badal gayi to ek dafa dobara koshish karo, sakht hidayaat ke saath.
    if language_changed(text, output):
        notes.append(
            "Language changed — retried with strict instructions."
        )
        strict = (
            prompts.SYSTEM
            + "\n\nDOBARA YAAD RAKHO: output BILKUL usi zubaan mein do jis mein "
            "draft hai. Tarjuma bilkul nahi. Ek lafz bhi doosri zubaan ka nahi."
        )
        try:
            retried = []
            for c in chunks:
                user = prompts.build_user_prompt(
                    c, tone, reading_level, strength, keep_length, profile=profile
                )
                raw = await provider.complete(strict, user, temperature=0.5)
                retried.append(postprocess.clean(raw))
            candidate = "\n\n".join(retried).strip()
            if not language_changed(text, candidate):
                output = candidate
            else:
                notes.append(
                    "Language still wrong after retry — try a different model."
                )
            after = readability.analyze(output)
        except Exception:
            notes.append("Language retry failed — original output returned.")

    # === QUALITY GUARD ===
    # Agar pehle rewrite ne text kharab kar diya, to ek repair pass chalao
    # aur DONO mein se behtar wala rakho. Kharab output kabhi na do.
    if needs_repair(before, after):
        try:
            repair_user = prompts.build_repair_prompt(
                output, readability.suggestions(after)
            )
            repaired = postprocess.clean(
                await provider.complete(
                    prompts.REPAIR_SYSTEM, repair_user, temperature=0.5
                )
            )
            repaired_metrics = readability.analyze(repaired)
            if repaired_metrics["naturalness_score"] > after["naturalness_score"]:
                output, after = repaired, repaired_metrics
                repair_used = True
                notes.append(
                    "First rewrite was too heavy, so a repair pass was applied."
                )
            else:
                notes.append(
                    "Rewrite did not improve the text — try a different strength or tone."
                )
        except Exception:
            # If repair fails, return the first rewrite — never crash.
            notes.append("Repair pass failed — first rewrite returned.")

    if len(chunks) > 1:
        notes.append(f"Text split into {len(chunks)} chunks and rewritten.")
    delta = after["naturalness_score"] - before["naturalness_score"]
    notes.append(
        f"Naturalness score {before['naturalness_score']} -> "
        f"{after['naturalness_score']} ({delta:+.1f})."
    )
    if delta < 0:
        notes.append("Score dropped — try a different strength or tone.")

    result = {
        "output": output,
        "provider_used": provider.name,
        "model_used": provider.model,
        "before": before,
        "after": after,
        "notes": notes,
        "voice_match": None,
        "voice_gaps": [],
        "profile_used": None,
        "repair_used": repair_used,
    }

    if profile:
        m = fp.match_score(profile["fingerprint"], fp.fingerprint(output))
        result["voice_match"] = m["voice_match"]
        result["voice_gaps"] = fp.explain_gaps(m["gaps"])
        result["profile_used"] = profile["name"]
        notes.insert(0, f"Voice match: {m['voice_match']}% ({profile['name']}).")
        if m["voice_match"] < 70:
            notes.append(
                "Voice match is low — try strength 3, or add more samples to your profile."
            )

    return result


async def rewrite_sentence(
    sentence: str,
    profile_id: str | None = None,
    tone: str = "blog",
    provider_name: str | None = None,
) -> str:
    """
    Ek jumla dobara likhna — 'per-sentence regenerate' button ke liye.
    Sasta aur foran, kyunki input chhota hai.
    """
    profile = style_profile.load_profile(profile_id) if profile_id else None
    provider = get_provider(provider_name)
    user = prompts.build_user_prompt(
        sentence, tone, "medium", 2, keep_length=False, profile=profile
    )
    raw = await provider.complete(prompts.SYSTEM, user, temperature=1.0)
    return postprocess.clean(raw)
