from app.web import TRANSLATION_LAB_HTML


def test_translation_lab_page_contains_runtime_hooks():
    html = TRANSLATION_LAB_HTML

    assert "/v1/models" in html
    assert "/admin/status" in html
    assert "/admin/switch/" in html
    assert "/v1/chat/completions" in html
    assert "ind_Latn" in html
    assert "target_lang = 'id'" in html
    assert "Mandarin Chinese" in html
    assert "Urdu" in html
