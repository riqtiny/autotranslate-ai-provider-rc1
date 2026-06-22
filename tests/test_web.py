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


def test_translation_lab_page_has_metrics_and_benchmark_hooks():
    html = TRANSLATION_LAB_HTML

    # Scoring endpoint + gold references drive the leaderboard.
    assert "/metrics/score" in html
    assert "cometToggle" in html
    assert "leaderboard" in html
    assert "ref:" in html  # gold reference shown per row

    # Throughput + device-aware memory.
    assert "tok/s" in html
    assert "Compute mode" in html
    assert "Throughput" in html
    assert "metricTps" in html
    assert "metricMode" in html

    # Benchmark explainer: what each metric measures.
    assert "What do these metrics measure?" in html
    assert "BLEU" in html
    assert "ChrF++" in html
    assert "COMET" in html
    assert "n-gram" in html
