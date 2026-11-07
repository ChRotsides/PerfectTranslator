import pytest

from perfect_translator.core import chunk_text, estimate_tokens


def test_empty_text_gives_no_chunks():
    assert chunk_text("") == []


def test_short_text_is_one_chunk():
    assert chunk_text("Hello world.\n", max_tokens=100) == ["Hello world.\n"]


def test_chunks_reassemble_exactly():
    text = "First line.\nSecond line, a bit longer than the first.\n\nThird paragraph here.\n" * 20
    chunks = chunk_text(text, max_tokens=30)
    assert len(chunks) > 1
    assert "".join(chunks) == text


def test_chunks_respect_token_limit():
    text = "\n".join(f"Sentence number {i} is here." for i in range(200))
    chunks = chunk_text(text, max_tokens=50)
    assert all(estimate_tokens(c) <= 50 for c in chunks)


def test_prefers_line_boundaries():
    text = "aaaa bbbb cccc\ndddd eeee ffff\n"
    chunks = chunk_text(text, max_tokens=estimate_tokens("aaaa bbbb cccc\n"))
    assert chunks == ["aaaa bbbb cccc\n", "dddd eeee ffff\n"]


def test_long_line_is_split_at_sentences():
    text = "One sentence here. Another sentence follows. A third one ends it."
    chunks = chunk_text(text, max_tokens=12)
    assert "".join(chunks) == text
    assert all(estimate_tokens(c) <= 12 for c in chunks)
    assert chunks[0].endswith(". ")


def test_giant_word_is_hard_split():
    text = "x" * 1000
    chunks = chunk_text(text, max_tokens=50)
    assert "".join(chunks) == text
    assert all(estimate_tokens(c) <= 50 for c in chunks)


def test_greek_text_counts_as_more_tokens_than_ascii():
    assert estimate_tokens("καλημέρα κόσμε") > estimate_tokens("hello world!!")


def test_unicode_text_round_trips_through_chunking():
    text = "Καλημέρα κόσμε. Αυτό είναι ένα τεστ.\n日本語の文章です。これはテストです。\nمرحبا بالعالم.\n" * 10
    chunks = chunk_text(text, max_tokens=40)
    assert "".join(chunks) == text
    assert all(estimate_tokens(c) <= 40 for c in chunks)


def test_custom_token_counter_is_used():
    chunks = chunk_text("a b c d e f", max_tokens=2, count_tokens=lambda s: len(s.split()))
    assert chunks == ["a b ", "c d ", "e f"]


def test_invalid_limit_rejected():
    with pytest.raises(ValueError):
        chunk_text("text", max_tokens=0)
