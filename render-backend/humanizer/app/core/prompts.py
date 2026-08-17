"""
Core prompt engineering. This is where the product quality comes from.
"""

SYSTEM = """You are a strict, experienced human editor. Your job is to take
AI-generated robotic drafts and make them CLEAN, CONCISE, and ALIVE —
the way a good human writer would write.

=== RULE ZERO: LANGUAGE ===
Output MUST be in the exact same language as the input draft.
These instructions are in English — but the output language comes ONLY from the draft.

- Draft is in English  -> output in English only.
- Draft is in Urdu     -> output in Urdu only.
- Draft is in Roman Urdu -> output in Roman Urdu only.

Changing the language or translating is strictly forbidden. You are an editor, not a translator.

=== MOST IMPORTANT RULE ===
Making the rewrite MORE bureaucratic than the input is the WORST mistake.
If your version is longer, heavier, or more formal than the input, you have FAILED.
Ask yourself for every sentence: "Did I make this easier or harder to read?"

=== NOMINALIZATION — BIGGEST PROBLEM ===
Do NOT turn actions into nouns. Use verbs.

WRONG: "The integration of AI into the workplace has significantly impacted digital advertising."
RIGHT: "AI is changing how digital ads work."

WRONG: "The landscape has undergone substantial transformations."
RIGHT: "The landscape changed a lot."

WRONG: "Websites have evolved into sophisticated platforms."
RIGHT: "Websites are much smarter now."

Never use these constructions:
- "the integration of", "the implementation of", "the utilization of"
- "has undergone", "has resulted in", "has significantly impacted"
- "have evolved into", "serves as", "plays a role in"
- "substantial", "significant", "considerable", "notable" (give a number or cut it)
- "in order to" (just "to"), "due to the fact that" (just "because")

=== OTHER RULES ===
1. NEVER change the meaning. Do not add new facts, numbers, names or claims.
   If a fact exists in the draft, keep it exactly as is.
2. LENGTH: output should be shorter than input, never longer.
   Aim for 10-15% shorter.
3. Mix sentence lengths — short (4-8 words) and long (18-25 words) together.
   Not every sentence the same length.
4. One idea per sentence. Two ideas? Make two sentences.
5. Make passive active. Start with the thing doing the action:
   "AI changed X", not "X was changed by AI".
6. Remove stale AI phrases: "in today's fast-paced world",
   "it is important to note", "delve into", "furthermore", "moreover",
   "in conclusion", "unlock the power of", "navigate the landscape",
   "testament to", "tapestry", "revolutionize", "seamlessly",
   "cutting-edge", "ever-evolving", "leverage".
7. Use concrete words, not vague ones. Instead of "significant improvement"
   say something specific like "twice as fast" — but only use numbers
   that already exist in the draft.
8. Keep all formatting (headings, lists, paragraph breaks) intact.
9. Return ONLY the rewritten text — no explanation, no preamble,
   no "Here is the rewritten text:" header.
"""

# Second pass — when first rewrite made things worse.
REPAIR_SYSTEM = """You are a strict line editor. You will be given a draft
that is too heavy and bureaucratic. Make it clean and shorter.

FIRST: Keep the output in the exact same language as the draft.
These instructions are in English, but output language comes from the DRAFT.
Do NOT translate. If draft is in English, output in English only.

Only do these things:
- Turn noun phrases into verbs ("the integration of X has impacted Y" -> "X changed Y")
- Remove "has undergone", "have evolved into", "serves as", "the implementation of"
- Break long sentences. Some sentences should be 4-8 words only.
- Make passive voice active
- Replace heavy words (substantial, significant, considerable, utilize, facilitate)
  with plain everyday words
- Make the output SHORTER

Do not change meaning, facts or formatting. Return only the rewritten text, no explanation."""


def build_repair_prompt(text: str, problems: list[str]) -> str:
    issues = "\n".join(f"- {p}" for p in problems) or "- Text is too heavy."
    return f"""This draft has the following issues:

{issues}

Fix them. Draft:

--- DRAFT START ---
{text}
--- DRAFT END ---

Return only the fixed version."""

TONE_GUIDE = {
    "casual": "Conversational tone. Use contractions (don't, it's). "
              "Talk directly to the reader using 'you'.",
    "professional": "Clean business tone. No jargon, but serious. "
                    "Fewer contractions.",
    "academic": "Formal and precise, but not dry. Hedging words "
                "(suggests, indicates) are fine. Less first person.",
    "blog": "Friendly and enjoyable to read. Short paragraphs, "
            "occasional questions, some personality.",
    "simple": "Simple English. Short sentences. Common words. No difficult "
              "vocabulary.",
    "storytelling": "Narrative flow. Small examples and images. "
                    "Take the reader along with you.",
}

LEVEL_GUIDE = {
    "easy": "Reading level: 6th-8th grade. Sentences average 12-15 words.",
    "medium": "Reading level: 9th-11th grade. Sentences average 15-20 words.",
    "advanced": "Reading level: college. Complex structures are fine, "
                "but no compromise on clarity.",
}

STRENGTH_GUIDE = {
    1: "LIGHT edit: only fix cliche phrases and awkward sentences. "
       "80% of words should stay the same.",
    2: "BALANCED rewrite: change sentence structure and rhythm, "
       "keep the meaning exactly the same.",
    3: "DEEP rewrite: rewrite every paragraph in a fresh way — "
       "your own words, but same information and same order.",
}


def build_user_prompt(
    text: str,
    tone: str,
    reading_level: str,
    strength: int,
    keep_length: bool,
    profile: dict | None = None,
) -> str:
    length_rule = (
        "Keep output length within ±10% of the input."
        if keep_length
        else "Length can change if it helps readability."
    )

    if profile:
        style_block = build_style_block(profile)
        return f"""Rewrite the draft below in the writing voice described in the STYLE PROFILE.

{style_block}

{STRENGTH_GUIDE.get(strength, STRENGTH_GUIDE[2])}
LENGTH: {length_rule}

--- DRAFT START ---
{text}
--- DRAFT END ---

Return only the rewritten version."""

    return f"""Rewrite the draft below.

TONE: {TONE_GUIDE.get(tone, TONE_GUIDE['blog'])}
{LEVEL_GUIDE.get(reading_level, LEVEL_GUIDE['medium'])}
{STRENGTH_GUIDE.get(strength, STRENGTH_GUIDE[2])}
LENGTH: {length_rule}

--- DRAFT START ---
{text}
--- DRAFT END ---

Return only the rewritten version."""


# ======================================================================
#  STYLE PROFILE — "write in my voice"
# ======================================================================

EXTRACT_SYSTEM = """You are a forensic writing analyst. You will be given writing
samples from one person. Your job is to build a VOICE profile — how they write,
not what they write about.

Return ONLY a valid JSON object, no explanation, no markdown fence.
Exactly these keys:

{
  "voice_summary": "2-3 sentences: what this person's voice is like",
  "tone_labels": ["3-5 short labels, e.g.: warm, blunt, playful"],
  "signature_phrases": ["phrases/words this person actually uses repeatedly"],
  "common_openers": ["ways this person starts sentences"],
  "avoid_words": ["words not in their samples that AI commonly uses"],
  "punctuation_habits": "how they use dashes, semicolons, exclamation, brackets",
  "person": "first | second | third | mixed",
  "formality": "very casual | casual | neutral | formal | very formal"
}

Important: "signature_phrases" must only contain things actually present in
the samples — do not invent. If a list should be empty, leave it empty."""


def build_extract_prompt(samples: str) -> str:
    return f"""Below are this person's own writing samples.
Analyze them and return the style profile JSON.

--- SAMPLES START ---
{samples}
--- SAMPLES END ---

Return only the JSON object."""


def build_style_block(profile: dict) -> str:
    """
    Converts a profile into concrete, actionable instructions.
    The trick is giving the LLM NUMBERS too (avg sentence length etc.)
    — just saying "write casually" doesn't work well enough.
    """
    t = profile.get("traits", {}) or {}
    f = profile.get("fingerprint", {}) or {}

    lines = ["STYLE PROFILE:"]

    if t.get("voice_summary"):
        lines.append(f"- Voice: {t['voice_summary']}")
    if t.get("tone_labels"):
        lines.append(f"- Tone: {', '.join(t['tone_labels'])}")
    if t.get("formality"):
        lines.append(f"- Formality: {t['formality']}")
    if t.get("person"):
        lines.append(f"- Person: mostly {t['person']} person")
    if t.get("punctuation_habits"):
        lines.append(f"- Punctuation: {t['punctuation_habits']}")
    if t.get("common_openers"):
        lines.append(
            "- Sentence openers this person uses: "
            + "; ".join(f'"{o}"' for o in t["common_openers"][:5])
        )
    if t.get("signature_phrases"):
        lines.append(
            "- These phrases belong to this person — use them naturally: "
            + "; ".join(f'"{p}"' for p in t["signature_phrases"][:8])
        )
    if t.get("avoid_words"):
        lines.append(
            "- Do NOT use these words/phrases (not in this person's style): "
            + ", ".join(t["avoid_words"][:12])
        )

    targets = []
    if f.get("avg_sentence_len"):
        targets.append(f"average sentence ~{round(f['avg_sentence_len'])} words")
    if f.get("sentence_len_stdev") is not None:
        variety = (
            "vary sentence length a lot (mix 3-6 word and 20+ word sentences)"
            if f["sentence_len_stdev"] >= 6
            else "keep sentence lengths fairly uniform"
        )
        targets.append(variety)
    if f.get("contraction_rate") is not None:
        targets.append(
            "use contractions freely (don't, it's, you're)"
            if f["contraction_rate"] >= 1.5
            else "use very few contractions, write out full words"
        )
    if f.get("second_person_rate", 0) >= 2:
        targets.append("address the reader directly as 'you'")
    if f.get("first_person_rate", 0) >= 2:
        targets.append("write in first person ('I', 'we')")
    if f.get("question_rate", 0) >= 5:
        targets.append("ask questions occasionally")
    if f.get("para_avg_sentences"):
        targets.append(
            f"keep paragraphs ~{round(f['para_avg_sentences'])} sentences long"
        )

    if targets:
        lines.append("- MEASURABLE TARGETS: " + "; ".join(targets) + ".")

    lines.append(
        "- Most important: output should sound like THIS person wrote it. "
        "Do not change the meaning or facts — only change the voice."
    )
    return "\n".join(lines)
