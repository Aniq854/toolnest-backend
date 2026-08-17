"""
STYLE FINGERPRINT — bina kisi LLM call ke, sirf maths se.

Yeh file aapke product ka moat hai. Har banday ki writing ke measurable
"habits" hoti hain: kitne lambe jumle, kitni contractions, kitne sawaal,
"main" zyada ya "aap" zyada. Yeh sab objectively naapa ja sakta hai —
aur isi liye yeh bilkul FREE hai (koi API call nahi) aur FAST hai.

Do jagah use hota hai:
  1. User ke samples se uski awaaz ka fingerprint banane ke liye
  2. Rewrite ke baad check karne ke liye ke output us awaaz se kitna milta hai
"""
import re

from app.core import readability

CONTRACTIONS = re.compile(
    r"\b\w+(?:'|’)(?:s|t|re|ve|ll|d|m)\b", re.IGNORECASE
)
FIRST_PERSON = re.compile(r"\b(?:i|me|my|mine|we|us|our|ours)\b", re.IGNORECASE)
SECOND_PERSON = re.compile(r"\b(?:you|your|yours|you're|youre)\b", re.IGNORECASE)


def _paragraphs(text: str) -> list[str]:
    return [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


def fingerprint(text: str) -> dict:
    """Text -> 10 numbers jo us writing ki 'habits' describe karte hain."""
    base = readability.analyze(text)
    words = readability.words_of(text)
    sents = readability.sentences_of(text)
    n_words = max(len(words), 1)
    n_sents = max(len(sents), 1)
    paras = _paragraphs(text)

    per100 = 100 / n_words

    return {
        # readability.py se dobara istemal
        "avg_sentence_len": base["avg_sentence_len"],
        "sentence_len_stdev": base["sentence_len_stdev"],
        "long_word_pct": base["long_word_pct"],
        "flesch_reading_ease": base["flesch_reading_ease"],
        # yahan ke naye signals
        "contraction_rate": round(len(CONTRACTIONS.findall(text)) * per100, 2),
        "first_person_rate": round(len(FIRST_PERSON.findall(text)) * per100, 2),
        "second_person_rate": round(len(SECOND_PERSON.findall(text)) * per100, 2),
        "comma_rate": round(text.count(",") / n_sents, 2),
        "question_rate": round(
            100 * sum(1 for s in sents if s.rstrip().endswith("?")) / n_sents, 2
        ),
        "para_avg_sentences": round(n_sents / max(len(paras), 1), 2),
    }


# Har signal ka (weight, tolerance).
# tolerance = itna farq "bilkul theek" mana jayega.
WEIGHTS = {
    "avg_sentence_len": (2.0, 3.0),
    "sentence_len_stdev": (1.5, 2.5),
    "contraction_rate": (1.5, 1.0),
    "second_person_rate": (1.2, 1.0),
    "first_person_rate": (1.2, 1.0),
    "long_word_pct": (1.0, 5.0),
    "comma_rate": (0.8, 0.7),
    "question_rate": (0.8, 4.0),
    "para_avg_sentences": (0.8, 1.5),
    "flesch_reading_ease": (1.0, 10.0),
}


def match_score(target: dict, actual: dict) -> dict:
    """
    Do fingerprints ka moqabla -> 0-100 "voice match" score.

    Har signal par: farq tolerance ke andar ho to 1.0, warna ghatta hua score.
    Phir weighted average. Saath hi bataata hai kaun sa signal off hai —
    yeh user ko dikhana hi trust banata hai (competitors black box dete hain).
    """
    total_w = 0.0
    earned = 0.0
    gaps: list[dict] = []

    for key, (weight, tol) in WEIGHTS.items():
        if key not in target or key not in actual:
            continue
        t, a = float(target[key]), float(actual[key])
        diff = abs(a - t)

        # tolerance ke andar = perfect; 4x tolerance par = 0
        if diff <= tol:
            sim = 1.0
        else:
            sim = max(0.0, 1.0 - (diff - tol) / (tol * 3))

        total_w += weight
        earned += sim * weight

        if sim < 0.75:
            gaps.append(
                {
                    "signal": key,
                    "your_style": round(t, 2),
                    "output": round(a, 2),
                    "direction": "zyada" if a > t else "kam",
                }
            )

    score = round(100 * earned / total_w, 1) if total_w else 0.0
    gaps.sort(key=lambda g: -abs(g["output"] - g["your_style"]))
    return {"voice_match": score, "gaps": gaps[:4]}


LABELS = {
    "avg_sentence_len": "jumlon ki lambai",
    "sentence_len_stdev": "jumlon ki variety",
    "contraction_rate": "contractions (don't, it's)",
    "second_person_rate": "'you' ka istemal",
    "first_person_rate": "'I/we' ka istemal",
    "long_word_pct": "bhaari lafz",
    "comma_rate": "commas",
    "question_rate": "sawaali jumle",
    "para_avg_sentences": "paragraph ki lambai",
    "flesch_reading_ease": "parhne ki aasani",
}


def explain_gaps(gaps: list[dict]) -> list[str]:
    return [
        f"{LABELS.get(g['signal'], g['signal'])}: aapke style se "
        f"{g['direction']} hai ({g['output']} vs {g['your_style']})."
        for g in gaps
    ]
