from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def test_name_is_linked_username_is_plain():
    src=(ROOT/'backend/app/services.py').read_text()
    assert "linked_name = f'<a href=" in src
    assert 'suffix = f" (@{escape(username.lstrip' in src
    assert '<a href="{href}"><b>{escape(name)}</b></a>' in src

def test_edit_notification_layout():
    src=(ROOT/'backend/app/services.py').read_text()
    assert 'f"💬 Диалог: <b>{escape(result.dialog.title' in src
    assert 'f"🕓 {_moment(result.message.edited_at)}\\n\\n"' in src
    assert 'f"<b>{label}</b>\\n"' in src
    assert 'f"🕓 {_moment(row.created_at)}\\n"' in src

def test_admin_navigation_and_user_dialogs():
    js=(ROOT/'web/admin.js').read_text()
    api=(ROOT/'backend/app/api.py').read_text()
    assert 'admin-sidebar' not in js
    assert "const pages={overview:'Обзор',users:'Пользователи',links:'Ссылки',payments:'Платежи',errors:'Ошибки',system:'Система'}" in js
    assert 'Посмотреть все диалоги' in js
    assert 'telegram-dialog-list' in js
    assert '@router.get("/admin/users/{user_id}/dialogs")' in api
    assert '@router.get("/admin/dialogs/{dialog_id}")' in api

def test_admin_charts_and_system_metrics():
    js=(ROOT/'web/admin.js').read_text()
    api=(ROOT/'backend/app/api.py').read_text()
    assert 'chart-readout' in js
    assert 'hourlyChart' in js
    assert 'Техническая нагрузка по часам' in js
    for field in ('memory_used','disk_used','hourly_24','failures_14','media_types'):
        assert field in api

def test_mobile_edge_safety():
    css=(ROOT/'web/styles.css').read_text()
    assert '.edge-safe' in css
    assert 'overflow-x:hidden' in css
    assert '.error-card-mobile p' in css
