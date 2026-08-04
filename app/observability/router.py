from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.observability.metrics import runtime_metrics

router = APIRouter(tags=["operations"])


@router.get("/metrics", include_in_schema=False, response_class=PlainTextResponse)
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(
        runtime_metrics.render_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
