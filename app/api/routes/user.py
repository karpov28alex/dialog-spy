from fastapi import APIRouter

from app.api.routes.dialog_export import router as dialog_export_router
from app.modules.account.router import require_channel_access
from app.modules.account.router import router as account_router
from app.modules.admin.router import router as admin_v2_router
from app.modules.archive.legacy_router import router as legacy_archive_router

router = APIRouter(prefix="/api", tags=["user"])
router.include_router(account_router)
router.include_router(legacy_archive_router)
router.include_router(dialog_export_router)
router.include_router(admin_v2_router)

__all__ = ["require_channel_access", "router"]
