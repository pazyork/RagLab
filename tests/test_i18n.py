import json
import os
import sys
from pathlib import Path

# Import the module directly to avoid importing the package __init__.py
i18n_dir = Path(__file__).parent.parent / "src" / "raglab" / "i18n"
sys.path.insert(0, str(i18n_dir))
from __init__ import t, set_lang, get_lang, _load_translations


def test_get_lang_default():
    """Test that default language is Chinese."""
    assert get_lang() == "zh"


def test_t_translates_existing_key_zh():
    """Test that t() returns correct Chinese translation for existing keys."""
    set_lang("zh")
    assert t("app.title") == "RagLab"
    assert t("nav.evaluate") == "评测"
    assert t("btn.start") == "开始评测"
    assert t("metric.cosine") == "余弦相似度"
    assert t("msg.saved") == "已保存"


def test_t_returns_key_for_nonexistent():
    """Test that t() returns the key itself when translation is not found."""
    assert t("nonexistent.key") == "nonexistent.key"
    assert t("") == ""


def test_set_lang_changes_language():
    """Test that set_lang() changes the current language."""
    set_lang("en")
    assert get_lang() == "en"
    assert t("app.title") == "RagLab"
    assert t("nav.evaluate") == "Evaluate"
    assert t("btn.start") == "Start Evaluation"
    assert t("metric.cosine") == "Cosine Similarity"
    assert t("msg.saved") == "Saved"

    set_lang("zh")
    assert get_lang() == "zh"
    assert t("nav.evaluate") == "评测"


def test_load_translations_returns_dict():
    """Test that _load_translations loads JSON correctly."""
    zh_trans = _load_translations("zh")
    assert isinstance(zh_trans, dict)
    assert "app.title" in zh_trans
    assert zh_trans["app.title"] == "RagLab"

    en_trans = _load_translations("en")
    assert isinstance(en_trans, dict)
    assert "app.title" in en_trans
    assert en_trans["app.title"] == "RagLab"


def test_translation_keys_consistent():
    """Test that zh and en JSON files have the same set of keys."""
    i18n_dir = Path(__file__).parent.parent / "src" / "raglab" / "i18n"

    with open(i18n_dir / "zh.json", "r", encoding="utf-8") as f:
        zh_keys = set(json.load(f).keys())

    with open(i18n_dir / "en.json", "r", encoding="utf-8") as f:
        en_keys = set(json.load(f).keys())

    # Check for keys missing in en.json
    missing_in_en = zh_keys - en_keys
    assert not missing_in_en, f"Keys missing in en.json: {missing_in_en}"

    # Check for keys missing in zh.json
    missing_in_zh = en_keys - zh_keys
    assert not missing_in_zh, f"Keys missing in zh.json: {missing_in_zh}"


def test_load_nonexistent_language():
    """Test that loading nonexistent language returns empty dict."""
    assert _load_translations("nonexistent") == {}


def test_t_works_after_language_switch():
    """Test that t() works correctly after multiple language switches."""
    set_lang("zh")
    assert t("btn.save") == "保存"

    set_lang("en")
    assert t("btn.save") == "Save"

    set_lang("zh")
    assert t("btn.save") == "保存"

    set_lang("en")
    assert t("btn.save") == "Save"
