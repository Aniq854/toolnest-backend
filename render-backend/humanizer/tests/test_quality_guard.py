"""
Yeh tests ek ASLI bug se aaye hain: tool ne input ko behtar karne ke bajaye
zyada bureaucratic bana diya tha. Yeh ab dobara na ho.
"""
from app.core import readability
from app.core.humanizer import needs_repair

# Asli misaal — user ka input
ORIGINAL = (
    "Artificial Intelligence is rapidly transforming the modern workplace, "
    "and digital advertising is no exception. The digital monetization "
    "landscape - once dominated by traditional static banner ads - has "
    "changed completely. Publishers now earn more from fewer placements."
)

# Asli misaal — tool ka KHARAB output (yehi bug tha)
BAD_REWRITE = (
    "The integration of Artificial Intelligence into the modern workplace "
    "has significantly impacted digital advertising, transforming the digital "
    "monetization landscape. The once traditional static banner "
    "ad-dominated landscape has undergone substantial transformations; "
    "modern websites have evolved into considerably more sophisticated "
    "platforms which serve as vehicles for the utilization of advanced "
    "monetization strategies."
)

# Aisa output jo waqai behtar hai
GOOD_REWRITE = (
    "AI is changing the modern workplace fast, and digital advertising is no "
    "exception. Static banner ads used to run the show. Not anymore. "
    "Publishers now earn more from fewer placements."
)


def test_bureaucratic_phrases_are_detected():
    assert readability.analyze(BAD_REWRITE)["bureaucracy_hits"] >= 5


def test_clean_text_has_no_bureaucracy():
    assert readability.analyze(GOOD_REWRITE)["bureaucracy_hits"] == 0


def test_bad_rewrite_scores_lower_than_original():
    """Yehi asli bug tha — output input se kharab tha."""
    before = readability.analyze(ORIGINAL)["naturalness_score"]
    after = readability.analyze(BAD_REWRITE)["naturalness_score"]
    assert after < before


def test_good_rewrite_scores_higher_than_original():
    before = readability.analyze(ORIGINAL)["naturalness_score"]
    after = readability.analyze(GOOD_REWRITE)["naturalness_score"]
    assert after > before


# ---------------- repair guard ----------------


def test_repair_triggers_on_bad_rewrite():
    assert needs_repair(
        readability.analyze(ORIGINAL), readability.analyze(BAD_REWRITE)
    )


def test_repair_does_not_trigger_on_good_rewrite():
    assert not needs_repair(
        readability.analyze(ORIGINAL), readability.analyze(GOOD_REWRITE)
    )


def test_repair_triggers_when_output_much_longer():
    before = {
        "naturalness_score": 50,
        "bureaucracy_hits": 0,
        "words": 100,
    }
    after = {"naturalness_score": 55, "bureaucracy_hits": 0, "words": 130}
    assert needs_repair(before, after)


def test_repair_triggers_when_bureaucracy_increases():
    before = {"naturalness_score": 50, "bureaucracy_hits": 1, "words": 100}
    after = {"naturalness_score": 60, "bureaucracy_hits": 4, "words": 95}
    assert needs_repair(before, after)


def test_no_repair_when_everything_improved():
    before = {"naturalness_score": 40, "bureaucracy_hits": 5, "words": 100}
    after = {"naturalness_score": 70, "bureaucracy_hits": 0, "words": 88}
    assert not needs_repair(before, after)


def test_suggestions_mention_bureaucracy():
    tips = readability.suggestions(readability.analyze(BAD_REWRITE))
    assert any("bureaucratic" in t.lower() for t in tips)


# ---------------- language guard ----------------
# Asli bug: English draft daala, output Roman Urdu mein aaya (kyunki system
# prompt Roman Urdu mein hai). Yeh dobara na ho.

from app.core.humanizer import language_changed  # noqa: E402

ENGLISH_DRAFT = (
    "Artificial Intelligence started as an idea in computer science and now "
    "runs the modern digital world. It includes machine learning and deep "
    "learning, which help systems learn from data, find patterns, and make "
    "their own decisions."
)

ROMAN_URDU_OUTPUT = (
    "AI ne computer science ki ek nazariya se shuru ki aur ab modern digital "
    "duniya ko chala rahi hai. AI mein machine learning aur deep learning "
    "jaise kai shakhayein hain jo systems ko data se seekhne, patterns "
    "pehchanne, aur apne decisions lene mein madad karti hain."
)

ENGLISH_REWRITE = (
    "AI began as an idea in computer science. Today it runs the digital world. "
    "Machine learning and deep learning let systems learn from data, spot "
    "patterns, and decide on their own."
)


def test_language_change_is_detected():
    assert language_changed(ENGLISH_DRAFT, ROMAN_URDU_OUTPUT)


def test_same_language_rewrite_passes():
    assert not language_changed(ENGLISH_DRAFT, ENGLISH_REWRITE)


def test_roman_urdu_input_stays_allowed():
    """Roman Urdu -> Roman Urdu bilkul jaiz hai, guard trigger na ho."""
    assert not language_changed(ROMAN_URDU_OUTPUT, ROMAN_URDU_OUTPUT)


def test_empty_text_does_not_crash():
    assert not language_changed("", "")
