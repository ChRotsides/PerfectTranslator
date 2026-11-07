from perfect_translator.core import (
    build_detection_messages,
    build_translation_messages,
    build_verification_messages,
    get_model,
)


def test_translation_messages_carry_languages_and_text():
    msgs = build_translation_messages("Καλημέρα", "Greek", "English")
    assert [m["role"] for m in msgs] == ["system", "user"]
    assert "Greek" in msgs[0]["content"] and "English" in msgs[0]["content"]
    assert msgs[1]["content"] == "Καλημέρα"  # text is passed through untouched


def test_translation_system_prompt_guards_against_injection():
    system = build_translation_messages("x", "A", "B")[0]["content"]
    assert "never instructions" in system
    assert "translation only" in system


def test_verification_messages_include_both_texts():
    msgs = build_verification_messages("orig text", "draft text", "French", "German")
    assert "orig text" in msgs[1]["content"] and "draft text" in msgs[1]["content"]
    assert "French" in msgs[0]["content"] and "German" in msgs[0]["content"]


def test_detection_messages_request_json():
    msgs = build_detection_messages("bonjour")
    assert "JSON" in msgs[0]["content"]
    assert msgs[1]["content"] == "bonjour"


def test_model_defaults_and_env_override(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    assert get_model() == "gpt-4o-mini"
    monkeypatch.setenv("OPENAI_MODEL", "  my-model ")
    assert get_model() == "my-model"
    monkeypatch.setenv("OPENAI_MODEL", "")
    assert get_model() == "gpt-4o-mini"
