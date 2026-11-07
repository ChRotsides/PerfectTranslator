import pytest
from conftest import FakeClient

from perfect_translator.core import (
    Detection,
    DetectionParseError,
    detect_language,
    parse_detection,
    sample_text,
)


def test_parse_valid_json():
    d = parse_detection('{"language": "Greek", "code": "EL", "confidence": 0.97}')
    assert d == Detection("Greek", "el", 0.97)


def test_parse_code_fenced_json():
    d = parse_detection('```json\n{"language": "French", "code": "fr", "confidence": 0.9}\n```')
    assert d.language == "French" and d.code == "fr"


def test_parse_json_with_surrounding_prose():
    d = parse_detection('Sure! {"language": "German", "code": "de", "confidence": 1} Hope that helps.')
    assert d.language == "German"


def test_confidence_is_clamped_and_coerced():
    assert parse_detection('{"language": "X", "code": "x", "confidence": 7}').confidence == 1.0
    assert parse_detection('{"language": "X", "code": "x", "confidence": -2}').confidence == 0.0
    assert parse_detection('{"language": "X", "code": "x", "confidence": "high"}').confidence == 0.0
    assert parse_detection('{"language": "X", "code": "x", "confidence": "0.5"}').confidence == 0.5


def test_missing_code_and_confidence_default():
    d = parse_detection('{"language": "Latin"}')
    assert d == Detection("Latin", "und", 0.0)


@pytest.mark.parametrize(
    "raw",
    ["", "   ", "Greek", "{not json", "[1, 2]", '{"code": "el"}', '{"language": ""}', '{"language": 5}'],
)
def test_malformed_replies_raise(raw):
    with pytest.raises(DetectionParseError):
        parse_detection(raw)


def test_detect_language_uses_json_mode_and_model():
    client = FakeClient(['{"language": "Spanish", "code": "es", "confidence": 0.99}'])
    d = detect_language("Hola, ¿cómo estás?", client=client, model="test-model")
    assert d.language == "Spanish"
    call = client.calls[0]
    assert call["model"] == "test-model"
    assert call["response_format"] == {"type": "json_object"}
    assert call["messages"][1]["content"] == "Hola, ¿cómo estás?"


def test_detect_language_returns_unknown_on_garbage_reply():
    client = FakeClient(["I think it's Greek"])
    assert detect_language("κείμενο", client=client, model="m") == Detection.unknown()


def test_detect_language_blank_text_makes_no_call():
    client = FakeClient([])
    assert detect_language("  \n ", client=client, model="m") == Detection.unknown()
    assert client.calls == []


def test_sample_text_short_is_unchanged_and_long_is_bounded():
    assert sample_text("  short  ") == "short"
    long_text = "a" * 10_000 + "b" * 10_000 + "c" * 10_000
    sample = sample_text(long_text, max_chars=300)
    assert len(sample) <= 300 + 2
    assert sample.startswith("a") and sample.endswith("c") and "b" in sample
