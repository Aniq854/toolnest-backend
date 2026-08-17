"""
Lamba text LLM ki ek request mein theek se rewrite nahi hota, aur context
limit bhi hai. Is liye paragraph boundaries par tor kar bhejte hain.
"""
import re


def split_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n", text.strip())
    return [p.strip() for p in parts if p.strip()]


def chunk_text(text: str, max_chars: int = 2500) -> list[str]:
    """Paragraph boundary par torta hai (jumla beech se nahi katta)."""
    paras = split_paragraphs(text)
    chunks: list[str] = []
    current = ""

    for p in paras:
        # ek hi paragraph limit se bara ho to jumlon par tor do
        if len(p) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            for sent_group in _split_long_paragraph(p, max_chars):
                chunks.append(sent_group)
            continue

        if len(current) + len(p) + 2 <= max_chars:
            current = f"{current}\n\n{p}" if current else p
        else:
            chunks.append(current.strip())
            current = p

    if current.strip():
        chunks.append(current.strip())
    return chunks or [text.strip()]


def _split_long_paragraph(para: str, max_chars: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", para)
    out, cur = [], ""
    for s in sentences:
        if len(cur) + len(s) + 1 <= max_chars:
            cur = f"{cur} {s}".strip()
        else:
            if cur:
                out.append(cur)
            cur = s
    if cur:
        out.append(cur)
    return out
