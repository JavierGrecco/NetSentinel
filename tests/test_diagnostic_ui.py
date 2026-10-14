from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "src/netsentinel/static/index.html"


def test_diagnostic_ui_labels_timeout_as_timeout_not_skipped():
    html = DASHBOARD.read_text(encoding="utf-8")

    assert "c.status==='timeout'?'warn'" in html
    assert "c.status==='error'?'Error de ejecución':'Omitido'" in html
    assert "c.error_code" in html
    assert "Falla local registrada en netsentinel-errors.jsonl." in html
    assert "No se registra como fallo interno" in html
    assert "No se pudo guardar el registro local" in html
