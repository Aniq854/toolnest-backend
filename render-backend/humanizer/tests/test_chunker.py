from app.core import postprocess
from app.core.chunker import chunk_text, split_paragraphs


def test_split_paragraphs():
    assert split_paragraphs("A\n\nB\n\n\nC") == ["A", "B", "C"]


def test_small_text_single_chunk():
    assert len(chunk_text("Hello world. This is small.", 2500)) == 1


def test_respects_max_chars():
    text = "\n\n".join(["Paragraph number %d here." % i for i in range(200)])
    chunks = chunk_text(text, 300)
    assert len(chunks) > 1
    assert all(len(c) <= 320 for c in chunks)


def test_no_content_lost():
    text = "\n\n".join(f"Para {i} content." for i in range(50))
    joined = " ".join(chunk_text(text, 200)).replace("\n", " ")
    for i in range(50):
        assert f"Para {i} content." in joined


def test_long_single_paragraph_is_split():
    para = " ".join(["This is a sentence with several words in it."] * 60)
    chunks = chunk_text(para, 400)
    assert len(chunks) > 1


def test_postprocess_strips_preamble():
    out = postprocess.clean("Here's the rewritten text:\n\nActual content here.")
    assert out == "Actual content here."


def test_postprocess_fixes_typography():
    out = postprocess.clean("He said “hi” — then left…")
    assert "“" not in out and "—" not in out and "…" not in out


def test_postprocess_unwraps_code_fence():
    assert postprocess.clean("```\nplain text\n```") == "plain text"
