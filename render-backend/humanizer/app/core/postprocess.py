"""
LLM ke output ki safai. Model kabhi kabhi preamble laga deta hai ya
typography aisi rakh deta hai jo AI-generated lagti hai.
"""
import re

PREAMBLES = [
    r"^here'?s the (?:rewritten|humanized|revised).*?:\s*",
    r"^here is the (?:rewritten|humanized|revised).*?:\s*",
    r"^sure[,!].*?:\s*",
    r"^rewritten (?:version|text)\s*:\s*",
    r"^\*\*?(?:rewritten|output)\*\*?\s*:\s*",
]

# AI text ki pehchan banne wali typography -> aam keyboard typography
TYPO_FIXES = {
    "—": " - ",
    "–": "-",
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
    "…": "...",
    " ": " ",
}


def clean(text: str) -> str:
    out = text.strip()

    for pat in PREAMBLES:
        out = re.sub(pat, "", out, flags=re.IGNORECASE | re.DOTALL)

    # kabhi model poora jawab ``` ke andar de deta hai
    fence = re.match(r"^```(?:\w+)?\s*\n(.*?)\n```$", out, flags=re.DOTALL)
    if fence:
        out = fence.group(1)

    for bad, good in TYPO_FIXES.items():
        out = out.replace(bad, good)

    out = re.sub(r"[ \t]+", " ", out)
    out = re.sub(r" +\n", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()
