from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def test_fast_dialog_cache_and_admin_pages():
    app=(ROOT/'web/app.js').read_text()
    admin=(ROOT/'web/admin.js').read_text()
    assert "cacheRead('dialogs')" in app
    assert "cacheWrite('dialogs'" in app
    assert "background-refresh" in app
    for page in ('overview','users','payments','errors','system'):
        assert page in admin
    for removed in ("subscriptions:'Подписки'","dialogs:'Диалоги'","events:'События'","media:'Хранилище'"):
        assert removed not in admin

def test_notifications_contain_profile_and_versions():
    services=(ROOT/'backend/app/services.py').read_text()
    worker=(ROOT/'backend/app/worker.py').read_text()
    assert 'https://t.me/' in services
    assert 'tg://user?id=' in services
    assert 'MessageVersion' in worker
    assert 'Все версии сохранены' in services

def test_admin_dashboard_endpoints():
    api=(ROOT/'backend/app/api.py').read_text()
    for path in ("/admin/dashboard","/admin/payments","/admin/errors","/admin/system"):
        assert path in api
