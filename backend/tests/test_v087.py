from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def test_native_navigation_links():
    app=(ROOT/'web/app.js').read_text()
    assert 'href="#/"' in app and 'href="#/profile"' in app
    assert 'href="#/dialogs/${d.id}"' in app
    assert 'class="icon-button back-button" href=' in app

def test_admin_back_and_media_links():
    admin=(ROOT/'web/admin.js').read_text(); api=(ROOT/'backend/app/api.py').read_text()
    assert 'href="#users/${userId}/dialogs"' in admin
    assert '/admin/media/{media_id}/link' in api and '/media/{media_id}/open' in api

def test_own_media_notifications_suppressed():
    src=(ROOT/'backend/app/telegram.py').read_text()
    assert 'is_own_outgoing = result.message.from_user_id == result.owner.telegram_id' in src
    assert 'and not is_own_outgoing' in src
