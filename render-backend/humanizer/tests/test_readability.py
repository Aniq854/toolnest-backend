from app.core import readability


ROBOTIC = (
    "In today's fast-paced world, it is important to note that businesses must "
    "leverage cutting-edge technology. Furthermore, the implementation of such "
    "solutions is considered essential by many organizations. Moreover, it is "
    "widely believed that companies which delve into these areas will be "
    "rewarded. In conclusion, the realm of digital transformation plays a "
    "crucial role in modern enterprise strategy."
)

NATURAL = (
    "Most businesses are behind on tech. That is a real problem. A retailer we "
    "worked with lost 40 percent of its online orders last year because the "
    "checkout page took nine seconds to load. They fixed it in a week. Orders "
    "recovered. The lesson is simple: small technical debts compound faster "
    "than anyone expects."
)


def test_basic_counts():
    m = readability.analyze("This is one. This is two.")
    assert m["sentences"] == 2
    assert m["words"] == 6


def test_cliches_detected():
    assert readability.analyze(ROBOTIC)["cliche_hits"] > 3
    assert readability.analyze(NATURAL)["cliche_hits"] == 0


def test_natural_scores_higher():
    robotic = readability.analyze(ROBOTIC)["naturalness_score"]
    natural = readability.analyze(NATURAL)["naturalness_score"]
    assert natural > robotic


def test_syllables():
    assert readability.count_syllables("cat") == 1
    assert readability.count_syllables("running") == 2
    assert readability.count_syllables("technology") >= 3


def test_suggestions_not_empty():
    assert len(readability.suggestions(readability.analyze(ROBOTIC))) >= 1


def test_score_bounds():
    for text in (ROBOTIC, NATURAL, "Short one. Two. Three."):
        s = readability.analyze(text)["naturalness_score"]
        assert 0 <= s <= 100
