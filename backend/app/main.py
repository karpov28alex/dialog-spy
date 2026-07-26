from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router as api_router, profile_bot
from .bootstrap import bootstrap
from .config import get_settings
from .telegram import router as telegram_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await bootstrap()
    yield
    await profile_bot.session.close()


app = FastAPI(title="Dialog Spy API", version="0.8.8", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.public_base_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(api_router)
app.include_router(telegram_router)
