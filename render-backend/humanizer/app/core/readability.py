"""
Bina kisi external library ke readability metrics. Yeh batate hain ke
rewrite se text waqai behtar hua ya nahi — yani ek objective "before/after".
"""
import re
import statistics

VOWELS = "aeiouy"

CLICHES = [
    "in today's fast-paced world", "it is important to note",
    "delve into", "furthermore", "moreover", "in conclusion",
    "unlock the power", "navigate the landscape", "a testament to",
    "tapestry", "revolutionize", "game-changer", "seamlessly",
    "cutting-edge", "at the end of the day", "when it comes to",
    "plays a crucial role", "it's worth noting", "the realm of",
    "embark on a journey", "ever-evolving", "leverage",
]

PASSIVE = re.compile(
    r"\b(?:is|are|was|were|be|been|being)\s+\w+(?:ed|en)\b", re.IGNORECASE
)

# Bureaucratic constructions — kaam ko noun bana dena. Yeh writing ko
# bhaari aur bekaar banata hai, aur AI rewriters ki sab se aam ghalti hai.
BUREAUCRATIC = re.compile(
    r"\b(?:"
    r"the\s+(?:integration|implementation|utilization|application|"
    r"introduction|adoption|transformation|optimization)\s+of"
    r"|has\s+(?:undergone|resulted\s+in|led\s+to|significantly\s+impacted)"
    r"|have\s+(?:undergone|evolved\s+into|resulted\s+in)"
    r"|serves?\s+as|plays?\s+a\s+(?:crucial\s+|key\s+|vital\s+)?role"
    r"|in\s+order\s+to|due\s+to\s+the\s+fact\s+that"
    r"|with\s+regard\s+to|for\s+the\s+purpose\s+of"
    r"|substantial(?:ly)?|significant(?:ly)?|considerable(?:y)?"
    r"|utilize[sd]?|facilitate[sd]?|endeavour|endeavor"
    r")\b",
    re.IGNORECASE,
)


def count_syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    count, prev_vowel = 0, False
    for ch in w:
        is_v = ch in VOWELS
        if is_v and not prev_vowel:
            count += 1
        prev_vowel = is_v
    if w.endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def sentences_of(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def words_of(text: str) -> list[str]:
    return re.findall(r"[A-Za-z'’]+", text)


def analyze(text: str) -> dict:
    sents = sentences_of(text)
    words = words_of(text)
    n_words = len(words) or 1
    n_sents = len(sents) or 1

    lengths = [len(words_of(s)) for s in sents] or [0]
    stdev = statistics.pstdev(lengths) if len(lengths) > 1 else 0.0

    syllables = sum(count_syllables(w) for w in words)
    long_words = sum(1 for w in words if count_syllables(w) >= 3)

    flesch = 206.835 - 1.015 * (n_words / n_sents) - 84.6 * (syllables / n_words)

    low = text.lower()
    cliche_hits = sum(low.count(c) for c in CLICHES)
    passive_hits = len(PASSIVE.findall(text))
    bureaucracy_hits = len(BUREAUCRATIC.findall(text))

    return {
        "words": len(words),
        "sentences": len(sents),
        "avg_sentence_len": round(n_words / n_sents, 2),
        "sentence_len_stdev": round(stdev, 2),
        "long_word_pct": round(100 * long_words / n_words, 2),
        "flesch_reading_ease": round(max(min(flesch, 120), -50), 2),
        "passive_hits": passive_hits,
        "cliche_hits": cliche_hits,
        "bureaucracy_hits": bureaucracy_hits,
        "naturalness_score": naturalness(
            stdev, cliche_hits, passive_hits, bureaucracy_hits, n_words, flesch
        ),
    }


def naturalness(
    stdev: float,
    cliches: int,
    passive: int,
    bureaucracy: int,
    n_words: int,
    flesch: float,
) -> float:
    """
    0-100 stable heuristic score based on writing quality signals:
      - sentence length variety (humans vary more)
      - cliche / AI phrase density
      - passive voice density
      - bureaucratic nominalizations
      - readability (Flesch)

    Redesigned to be stable and predictable — no more wild swings.
    A clean, natural text scores 55-75. Heavy AI text scores 10-30.
    """
    per_1k = 1000 / max(n_words, 1)

    # Variety: 0-25 pts. Good human writing has stdev 4-8.
    variety = min(stdev / 8.0, 1.0) * 25

    # Readability: 0-30 pts. Flesch 50-80 is the sweet spot.
    read = max(0.0, min((flesch - 10) / 70, 1.0)) * 30

    # Base score is 45 (neither good nor bad).
    base = 45.0

    # Penalties — capped more tightly to avoid wild swings.
    cliche_pen = min(cliches * per_1k * 3.0, 20)   # max -20
    passive_pen = min(passive * per_1k * 1.0, 15)  # max -15
    bureau_pen = min(bureaucracy * per_1k * 2.5, 20) # max -20

    score = base + variety + read - cliche_pen - passive_pen - bureau_pen
    return round(max(0.0, min(score, 100.0)), 1)


def suggestions(m: dict) -> list[str]:
    out = []
    if m.get("bureaucracy_hits", 0) > 0:
        out.append(
            f"{m['bureaucracy_hits']} bureaucratic constructions mile "
            '("the integration of...", "has undergone...") — inhein seedhe '
            "verbs se badlein."
        )
    if m["sentence_len_stdev"] < 4:
        out.append("Sab jumle qareeb qareeb ek hi lambai ke hain — kuch chhote "
                   "(4-8 lafz) jumle daalein taake rhythm bane.")
    if m["cliche_hits"] > 0:
        out.append(f"{m['cliche_hits']} ghisay pitay AI phrases mile — inko "
                   "specific baat se replace karein.")
    if m["passive_hits"] > max(3, m["sentences"] * 0.25):
        out.append("Passive voice zyada hai — active voice mein badlein.")
    if m["flesch_reading_ease"] < 40:
        out.append("Parhna mushkil hai — lambe jumle torein aur aasan lafz "
                   "istemal karein.")
    if m["long_word_pct"] > 25:
        out.append("Bhaari (3+ syllable) lafz zyada hain — saada mutabadil "
                   "dhoondein.")
    if not out:
        out.append("Text ke basic quality signals theek lag rahe hain.")
    return out
