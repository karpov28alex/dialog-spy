from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP = (ROOT / "web/app.js").read_text(encoding="utf-8")
ADMIN = (ROOT / "web/admin.js").read_text(encoding="utf-8")
API = (ROOT / "backend/app/api.py").read_text(encoding="utf-8")


def test_telegram_is_initialized_even_with_cached_auth():
    assert "initializeTelegram();render()" in APP
    assert "tg.requestFullscreen?.()" in APP
    assert "requestAnimationFrame(expand)" in APP


def test_navigation_uses_one_delegated_route_and_back_handler():
    assert "closest('[data-go]')||target.closest('a[href^=\"#/\"]')" in APP
    assert "if(!telegramBackHandler)" in APP
    assert "b.offClick?.(window.__dsBackHandler)" in APP
    assert "backTarget(normalizePath(location.hash.slice(1)||'/'))" in APP
    assert "requestSeq++;location.hash=path" in APP


def test_referral_modal_uses_existing_visible_overlay_and_refreshes_first():
    assert 'class="admin-detail-backdrop open" id="link-modal"' in ADMIN
    start = ADMIN.index("const d=await api('/referral-links'", ADMIN.index("function createLinkModal"))
    created = ADMIN[start:ADMIN.index("}catch(err)", start)]
    assert created.index("await links()") < created.index("navigator.clipboard.writeText")


def test_referral_creation_does_not_commit_before_get_me():
    block = API[API.index("async def create_referral_link"):API.index('@router.get("/admin/referral-links")')]
    assert block.index("profile_bot.get_me()") < block.index("await db.commit()")
