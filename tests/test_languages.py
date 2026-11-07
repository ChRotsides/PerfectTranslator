from perfect_translator.languages import LANGUAGES


def test_language_list_is_sane():
    assert "English" in LANGUAGES and "Greek" in LANGUAGES
    assert len(LANGUAGES) == len(set(LANGUAGES))
