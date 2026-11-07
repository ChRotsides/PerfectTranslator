import pytest
from conftest import FakeClient, rate_limit_error

from perfect_translator.core import (
    TranslationError,
    make_client,
    read_text_file,
    translate_chunk,
    translate_file,
    translate_text,
    write_text_file,
)

DETECT_EN = '{"language": "English", "code": "en", "confidence": 0.99}'


def echo_upper(kwargs):
    return kwargs["messages"][-1]["content"].upper()


def test_translate_chunk_preserves_edge_whitespace():
    client = FakeClient(["bonjour"])
    assert translate_chunk("\n  hello \n\n", "English", "French", client, "m") == "\n  bonjour \n\n"
    # the model never sees the padding
    assert client.calls[0]["messages"][1]["content"] == "hello"


def test_translate_chunk_whitespace_only_makes_no_call():
    client = FakeClient([])
    assert translate_chunk(" \n", "A", "B", client, "m") == " \n"
    assert client.calls == []


def test_verify_pass_replaces_draft():
    client = FakeClient(["draft", "final"])
    assert translate_chunk("src", "A", "B", client, "m", verify=True) == "final"
    assert len(client.calls) == 2


def test_verify_failure_falls_back_to_draft(no_sleep):
    sleep, _ = no_sleep
    client = FakeClient(["draft", rate_limit_error()])
    assert translate_chunk("src", "A", "B", client, "m", verify=True, sleep=sleep) == "draft"


def test_empty_reply_is_an_error():
    with pytest.raises(TranslationError):
        translate_chunk("src", "A", "B", FakeClient(["   "]), "m")


def test_translate_text_detects_source_then_translates_in_order():
    text = "Line one.\nLine two.\nLine three.\n"
    client = FakeClient([DETECT_EN, echo_upper])
    result = translate_text(text, "Greek", client=client, model="m", max_chunk_tokens=5, workers=1)
    assert result.source_language == "English"
    assert result.chunk_count == len(client.calls) - 1 > 1
    assert result.text == text.upper()
    assert result.failed_chunks == []


def test_translate_text_skips_detection_when_source_given():
    client = FakeClient([echo_upper])
    result = translate_text("hi", "Greek", source="English", client=client, model="m")
    assert result.text == "HI"
    assert all("response_format" not in c for c in client.calls)


def test_concurrent_workers_keep_chunk_order():
    text = "".join(f"Paragraph {i}.\n" for i in range(12))
    client = FakeClient([echo_upper])
    result = translate_text(
        text, "Greek", source="English", client=client, model="m", max_chunk_tokens=5, workers=4
    )
    assert result.chunk_count == 12
    assert result.text == text.upper()


def test_failed_chunk_keeps_original_text_and_is_reported(no_sleep):
    sleep, _ = no_sleep
    text = "Aaaa.\nBbbb.\n"

    def reply(kwargs):
        content = kwargs["messages"][-1]["content"]
        if "Bbbb" in content:
            raise rate_limit_error()
        return content.upper()

    progress = []
    result = translate_text(
        text,
        "Greek",
        source="English",
        client=FakeClient([reply]),
        model="m",
        max_chunk_tokens=2,
        workers=1,
        sleep=sleep,
        on_progress=lambda done, total: progress.append((done, total)),
    )
    assert result.failed_chunks == [1]
    assert result.text == "AAAA.\nBbbb.\n"
    assert progress[-1] == (2, 2)


def test_blank_text_makes_no_calls():
    client = FakeClient([])
    result = translate_text("  \n", "Greek", client=client)
    assert result.text == "  \n" and result.chunk_count == 0
    assert client.calls == []


def test_file_round_trip_with_unicode(tmp_path):
    src = tmp_path / "in.txt"
    dst = tmp_path / "out.txt"
    original = "Καλημέρα κόσμε.\r\n日本語。\nعربى\n"
    src.write_bytes(original.encode("utf-8"))
    result = translate_file(src, dst, "English", source="Greek", client=FakeClient([echo_upper]), model="m")
    assert dst.read_bytes().decode("utf-8") == original.upper()
    assert result.failed_chunks == []


def test_read_strips_bom_and_keeps_newlines(tmp_path):
    p = tmp_path / "bom.txt"
    p.write_bytes("﻿a\r\nb\n".encode())
    assert read_text_file(p) == "a\r\nb\n"
    write_text_file(p, "ä\r\nö\n")
    assert p.read_bytes() == "ä\r\nö\n".encode()


def test_non_utf8_file_gives_clear_error(tmp_path):
    p = tmp_path / "latin.txt"
    p.write_bytes(b"caf\xe9")
    with pytest.raises(TranslationError, match="UTF-8"):
        read_text_file(p)


def test_make_client_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("perfect_translator.core.load_env", lambda: None)
    with pytest.raises(TranslationError, match="OPENAI_API_KEY"):
        make_client()


def test_make_client_builds_without_network(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    monkeypatch.setattr("perfect_translator.core.load_env", lambda: None)
    assert make_client().max_retries == 0
