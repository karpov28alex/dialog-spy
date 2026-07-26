from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
ADMIN = (ROOT / "web" / "admin.js").read_text(encoding="utf-8")
CSS = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
API = (ROOT / "backend" / "app" / "api.py").read_text(encoding="utf-8")
SERVICES = (ROOT / "backend" / "app" / "services.py").read_text(encoding="utf-8")


def test_miniapp_navigation_is_delegated_and_has_native_back():
    assert "document.addEventListener('click'" in APP
    assert "closest('[data-go]')" in APP
    assert "closest('[data-back]')" in APP
    assert "syncTelegramBack(route)" in APP
    assert "path.startsWith('/dialogs/')?'/':" in APP
    assert "class=\"icon-button back-button\" href=" in APP


def test_dialog_back_path_is_explicit():
    assert "chat-menu" in APP
    assert "`,'/')}<section class=\"chat-wall\"" in APP


def test_admin_media_can_be_opened_securely():
    assert '@router.get("/admin/media/{media_id}/download")' in API
    assert "current_admin" in API
    assert "data-admin-media" in ADMIN
    assert "openAdminMedia" in ADMIN
    assert "admin-media-viewer" in ADMIN


def test_mobile_black_strip_hardening():
    assert ".admin-body,.admin-body #root,.admin-app,.admin-content,.admin-page,.admin-login" in CSS
    assert "overflow-x:hidden!important" in CSS
    assert ".admin-chat-page{width:100%!important" in CSS
    assert ".admin-login{min-height:100dvh" in CSS


def test_graphs_have_visible_readout_and_touch_selection():
    assert "polished-chart" in ADMIN
    assert "chart-grid-lines" in ADMIN
    assert "data-chart-series" in ADMIN
    assert "pointerdown" in ADMIN
    assert ".chart-point.active" in CSS


def test_notification_profile_layout_is_name_link_only():
    assert "linked_name = f'<a href=\"{href}\"><b>{escape(name)}</b></a>'" in SERVICES
    assert 'suffix = f" (@{escape(username.lstrip(\'@\'))})" if username else ""' in SERVICES
    assert "return f\"👤 {linked_name}{suffix}\"" in SERVICES
