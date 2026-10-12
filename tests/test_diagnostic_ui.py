from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "src/netsentinel/static/index.html"


def test_diagnostic_ui_labels_timeout_as_timeout_not_skipped():
    html = DASHBOARD.read_text(encoding="utf-8")

    assert "c.status==='timeout'?'warn'" in html
    assert "c.status==='timeout'?'Tiempo agotado':'Omitido'" in html
