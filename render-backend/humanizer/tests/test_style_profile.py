import asyncio

import pytest

from app.core import fingerprint as fp
from app.core import prompts, style_profile

MY_VOICE = (
    "I don't think most people get this. You've probably felt it too.\n\n"
    "Here's the thing: I spent three years building tools nobody wanted. "
    "Three years. And the whole time I told myself the market just wasn't "
    "ready yet. It was ready. I wasn't listening.\n\n"
    "So what changed? I started talking to people before writing code. "
    "That's it. That's the whole trick. You don't need a framework for it."
)

FORMAL_VOICE = (
    "It is widely acknowledged that organizational transformation requires "
    "sustained executive commitment over an extended period of time. "
    "Research conducted across multiple sectors indicates that initiatives "
    "lacking such commitment demonstrate substantially reduced probability "
    "of successful implementation. Consequently, practitioners are advised "
    "to secure appropriate sponsorship prior to commencement of any "
    "significant change programme within the enterprise environment."
)


# ---------------- fingerprint ----------------


def test_fingerprint_has_all_signals():
    f = fp.fingerprint(MY_VOICE)
    for key in fp.WEIGHTS:
        assert key in f, f"{key} missing"


def test_casual_voice_has_more_contractions():
    assert (
        fp.fingerprint(MY_VOICE)["contraction_rate"]
        > fp.fingerprint(FORMAL_VOICE)["contraction_rate"]
    )


def test_casual_voice_uses_more_second_person():
    assert (
        fp.fingerprint(MY_VOICE)["second_person_rate"]
        > fp.fingerprint(FORMAL_VOICE)["second_person_rate"]
    )


def test_formal_voice_has_longer_sentences():
    assert (
        fp.fingerprint(FORMAL_VOICE)["avg_sentence_len"]
        > fp.fingerprint(MY_VOICE)["avg_sentence_len"]
    )


def test_question_rate_detected():
    assert fp.fingerprint(MY_VOICE)["question_rate"] > 0
    assert fp.fingerprint(FORMAL_VOICE)["question_rate"] == 0


# ---------------- match score ----------------


def test_identical_text_scores_high():
    f = fp.fingerprint(MY_VOICE)
    assert fp.match_score(f, f)["voice_match"] == 100.0


def test_different_voices_score_low():
    m = fp.match_score(fp.fingerprint(MY_VOICE), fp.fingerprint(FORMAL_VOICE))
    assert m["voice_match"] < 60
    assert len(m["gaps"]) > 0


def test_score_always_in_bounds():
    for a in (MY_VOICE, FORMAL_VOICE):
        for b in (MY_VOICE, FORMAL_VOICE):
            s = fp.match_score(fp.fingerprint(a), fp.fingerprint(b))["voice_match"]
            assert 0 <= s <= 100


def test_gaps_are_explainable():
    m = fp.match_score(fp.fingerprint(MY_VOICE), fp.fingerprint(FORMAL_VOICE))
    lines = fp.explain_gaps(m["gaps"])
    assert lines and all(isinstance(x, str) and x for x in lines)


# ---------------- traits parsing ----------------


def test_parse_json_plain():
    assert style_profile._parse_json('{"person": "first"}')["person"] == "first"


def test_parse_json_with_fence():
    raw = 'Here you go:\n```json\n{"person": "second"}\n```'
    assert style_profile._parse_json(raw)["person"] == "second"


def test_parse_json_with_surrounding_text():
    raw = 'Sure! {"formality": "casual"} Hope that helps.'
    assert style_profile._parse_json(raw)["formality"] == "casual"


def test_parse_json_broken_falls_back():
    out = style_profile._parse_json("not json at all")
    assert out == style_profile.EMPTY_TRAITS


def test_clean_traits_coerces_string_to_list():
    out = style_profile._clean_traits({"tone_labels": "warm, blunt, funny"})
    assert out["tone_labels"] == ["warm", "blunt", "funny"]


def test_clean_traits_fills_missing_keys():
    out = style_profile._clean_traits({})
    assert set(out.keys()) == set(style_profile.EMPTY_TRAITS.keys())


def test_slugify():
    assert style_profile.slugify("Mera Blog Style!") == "mera-blog-style"
    assert style_profile.slugify("!!!") == "profile"


# ---------------- storage ----------------


@pytest.fixture
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(style_profile, "PROFILE_DIR", tmp_path / "profiles")
    return tmp_path


def _sample_profile(name="Test Voice"):
    return {
        "id": style_profile.slugify(name),
        "name": name,
        "created_at": "2026-01-01T00:00:00+00:00",
        "sample_word_count": 200,
        "fingerprint": fp.fingerprint(MY_VOICE),
        "traits": style_profile._clean_traits(
            {"voice_summary": "Blunt and direct.", "tone_labels": ["blunt"]}
        ),
    }


def test_save_and_load_roundtrip(tmp_store):
    style_profile.save_profile(_sample_profile())
    loaded = style_profile.load_profile("test-voice")
    assert loaded["name"] == "Test Voice"
    assert loaded["fingerprint"]["contraction_rate"] > 0


def test_load_missing_returns_none(tmp_store):
    assert style_profile.load_profile("nope") is None


def test_list_profiles(tmp_store):
    style_profile.save_profile(_sample_profile("One"))
    style_profile.save_profile(_sample_profile("Two"))
    ids = {p["id"] for p in style_profile.list_profiles()}
    assert ids == {"one", "two"}


def test_delete_profile(tmp_store):
    style_profile.save_profile(_sample_profile())
    assert style_profile.delete_profile("test-voice") is True
    assert style_profile.load_profile("test-voice") is None
    assert style_profile.delete_profile("test-voice") is False


def test_build_profile_rejects_short_samples(tmp_store):
    with pytest.raises(ValueError, match="bohat chhote"):
        asyncio.run(style_profile.build_profile("X", ["too short"]))


# ---------------- prompt injection ----------------


def test_style_block_includes_measurable_targets():
    block = prompts.build_style_block(_sample_profile())
    assert "MEASURABLE TARGETS" in block
    assert "average sentence" in block


def test_style_block_includes_avoid_words():
    profile = _sample_profile()
    profile["traits"]["avoid_words"] = ["delve", "furthermore"]
    block = prompts.build_style_block(profile)
    assert "delve" in block and "furthermore" in block


def test_profile_prompt_overrides_tone_preset():
    with_profile = prompts.build_user_prompt(
        "Some draft text here.", "academic", "advanced", 2, True, _sample_profile()
    )
    assert "STYLE PROFILE" in with_profile
    # tone preset ka text profile mode mein nahi hona chahiye
    assert prompts.TONE_GUIDE["academic"] not in with_profile


def test_prompt_without_profile_uses_tone_preset():
    plain = prompts.build_user_prompt("Some draft.", "academic", "advanced", 2, True)
    assert prompts.TONE_GUIDE["academic"] in plain
    assert "STYLE PROFILE" not in plain
