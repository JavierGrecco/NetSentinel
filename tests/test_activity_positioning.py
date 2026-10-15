from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_PAGE = ROOT / "src/netsentinel/static/activity.html"
README = ROOT / "README.md"
SECURITY = ROOT / "docs/SECURITY.md"
EXTENSION_GUIDE = ROOT / "browser-extension/README.md"


def test_activity_module_is_positioned_as_authorized_telemetry():
    page = ACTIVITY_PAGE.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")

    assert "<title>NetSentinel · Actividad y telemetría</title>" in page
    assert ">Actividad y telemetría</h1>" in page
    assert "Fuentes autorizadas" in page
    assert "actividad y telemetría autorizada" in readme.lower()
    assert "Actividad familiar" not in page
    assert "Actividad familiar" not in readme


def test_activity_docs_require_authorized_transparent_collection():
    security = SECURITY.read_text(encoding="utf-8").lower()
    extension = EXTENSION_GUIDE.read_text(encoding="utf-8").lower()

    assert "telemetría de actividad autorizada" in security
    assert "administrás con autorización" in extension
    assert "informá a las personas responsables" in extension
