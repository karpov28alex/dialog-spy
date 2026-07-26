from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent


def test_dialog_identity_ignores_connection_id():
    source = (ROOT / "app/services.py").read_text()
    block = source[source.index("async def ensure_dialog"):source.index("async def download_media")]
    assert "Dialog.owner_id == owner_id" in block
    assert "Dialog.telegram_chat_id == chat_id" in block
    assert "Dialog.connection_id == connection_id" not in block


def test_legacy_dialog_merge_is_wired_into_bootstrap():
    source = (ROOT / "app/bootstrap.py").read_text()
    assert "merge_duplicate_dialogs" in source
    assert "UPDATE messages AS m" in source
    assert "UPDATE events AS e" in source
    assert "uq_dialog_owner_chat" in source


def test_admin_has_dedicated_entrypoint():
    dockerfile = (PROJECT / "web/Dockerfile").read_text()
    nginx = (PROJECT / "web/nginx.conf").read_text()
    assert "COPY admin.html" in dockerfile
    assert "COPY admin.js" in dockerfile
    assert "location = /admin/" in nginx
    assert "try_files /admin.html" in nginx


def test_profile_switches_are_optimistic():
    source = (PROJECT / "web/app.js").read_text()
    start = source.index("document.querySelectorAll('[data-setting]')")
    end = source.index("document.getElementById('logout')", start)
    block = source[start:end]
    assert "sw?.classList.toggle('on',next)" in block
    assert "HapticFeedback?.selectionChanged" in block
    assert "profilePage(requestSeq)" not in block
