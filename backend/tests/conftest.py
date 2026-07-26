import os
import sys
import types
from pathlib import Path

from sqlalchemy.orm import DeclarativeBase

os.environ.setdefault("BOT_TOKEN", "123456789:test-token")
os.environ.setdefault("PUBLIC_BASE_URL", "https://example.test")
os.environ.setdefault("MINI_APP_URL", "https://example.test/app/")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://unused:unused@localhost/unused")
os.environ.setdefault("JWT_SECRET", "x" * 32)
os.environ.setdefault("WEBHOOK_SECRET", "y" * 24)
os.environ.setdefault("ADMIN_EMAIL", "admin@example.test")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-strong")
os.environ.setdefault("DEV_AUTH", "true")

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


class TestBase(DeclarativeBase):
    pass


fake_db = types.ModuleType("app.db")
fake_db.Base = TestBase
sys.modules.setdefault("app.db", fake_db)
