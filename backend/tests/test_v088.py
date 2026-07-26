from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def test_referral_models_and_routes():
 s=(ROOT/'backend/app/models.py').read_text(); a=(ROOT/'backend/app/api.py').read_text(); t=(ROOT/'backend/app/telegram.py').read_text()
 assert 'class ReferralLink' in s and 'referral_link_id' in s and 'bot_blocked_at' in s
 assert '/admin/referral-links' in a and 'cost_per_vip' in a
 assert 'payload.startswith("ref_")' in t
def test_admin_protected_media():
 s=(ROOT/'backend/app/services.py').read_text(); t=(ROOT/'backend/app/telegram.py').read_text(); w=(ROOT/'backend/app/worker.py').read_text()
 assert 'notify_admin_protected_media' in s
 assert 'admin_protected_media' in t and 'admin_protected_media' in w
def test_links_ui():
 s=(ROOT/'web/admin.js').read_text()
 assert "links:'Ссылки'" in s and 'createLinkModal' in s and 'Цена VIP' in s
