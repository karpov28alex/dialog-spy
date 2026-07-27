from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TELEGRAM = (ROOT / "backend/app/telegram.py").read_text(encoding="utf-8")
APP = (ROOT / "web/app.js").read_text(encoding="utf-8")
ADMIN = (ROOT / "web/admin.js").read_text(encoding="utf-8")


def test_only_protected_reply_media_is_delivered_to_owner():
    protected = TELEGRAM[TELEGRAM.index("protected_reply ="):TELEGRAM.index("result = await upsert_message(db, bot, business_message")]
    ordinary = TELEGRAM[TELEGRAM.index("result = await upsert_message(db, bot, business_message"):TELEGRAM.index("edited_message =")]
    assert "if media.is_ephemeral_hint" in protected
    assert "media_notifications.extend" not in ordinary
    assert "if not result.media" in ordinary


def test_back_handler_replaces_a_handler_left_by_an_old_cached_bundle():
    block = APP[APP.index("function syncTelegramBack"):APP.index("function avatar")]
    assert "b.offClick?.(window.__dsBackHandler)" in block
    assert "telegramBackHandler=()=>" in block
    assert "b.onClick?.(telegramBackHandler)" in block


def test_fullscreen_is_reapplied_when_telegram_viewport_changes():
    assert "tg.onEvent?.('viewportChanged',expand)" in APP


def test_referral_creation_uses_native_form_submission():
    block = ADMIN[ADMIN.index("function createLinkModal"):ADMIN.index("async function openLinkDetail")]
    assert '<form class="admin-detail" id="link-form">' in block
    assert 'type="submit"' in block
    assert "document.getElementById('link-form').onsubmit" in block
    assert "e.preventDefault()" in block


def test_frontend_cache_version_is_derived_from_asset_contents():
    dockerfile = (ROOT / "web/Dockerfile").read_text(encoding="utf-8")
    nginx = (ROOT / "web/nginx.conf").read_text(encoding="utf-8")
    index = (ROOT / "web/index.html").read_text(encoding="utf-8")
    admin_html = (ROOT / "web/admin.html").read_text(encoding="utf-8")
    assert "sha256sum" in dockerfile
    assert "s/__ASSET_VERSION__/${asset_version}/g" in dockerfile
    assert "?v=__ASSET_VERSION__" in index
    assert "?v=__ASSET_VERSION__" in admin_html
    assert 'max-age=31536000, immutable' in nginx
    assert 'no-store, no-cache, must-revalidate' in nginx


def test_build_version_is_visible_outside_render_roots():
    index = (ROOT / "web/index.html").read_text(encoding="utf-8")
    admin_html = (ROOT / "web/admin.html").read_text(encoding="utf-8")
    styles = (ROOT / "web/styles.css").read_text(encoding="utf-8")
    for html in (index, admin_html):
        assert '<div class="build-version"' in html
        assert 'v0.8.9 · __ASSET_VERSION__' in html
        assert html.index('id="root"') < html.index('class="build-version"')
    assert '.build-version{position:fixed' in styles
    assert 'pointer-events:none' in styles
