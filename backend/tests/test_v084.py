from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def test_back_navigation_and_no_red_badges():
    js=(ROOT/'web/app.js').read_text()
    assert 'data-back' in js
    assert 'backTo(' in js
    assert 'deleted-count">${d.deleted}' not in js

def test_unified_notification_person_and_dates():
    src=(ROOT/'backend/app/services.py').read_text()
    assert 'linked_name' in src
    assert 'suffix = f" (@{escape(username.lstrip' in src
    assert 'f"💬 Диалог:' in src
    assert 'f"🕓 {_moment(result.message.edited_at)}' in src
    assert 'f"<b>{label}</b>\\n"' in src

def test_admin_has_no_events_or_storage_pages():
    js=(ROOT/'web/admin.js').read_text()
    assert "events:'События'" not in js
    assert "media:'Хранилище'" not in js
    assert "subscriptions:'Подписки'" not in js
    assert "dialogs:'Диалоги'" not in js
    assert 'showUser' in js
    assert 'chart-readout' in js

def test_user_detail_endpoint_exists():
    src=(ROOT/'backend/app/api.py').read_text()
    assert '@router.get("/admin/users/{user_id}")' in src
    assert 'protected_media' in src
