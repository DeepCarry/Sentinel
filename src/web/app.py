import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from src.database import init_db
from src.web.routes import router
from src.logger import setup_logger

_WEB_DIR = os.path.dirname(os.path.abspath(__file__))
IS_VERCEL = os.getenv("VERCEL") is not None

logger = setup_logger("sentinel.web")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Database...")
    init_db()

    if not IS_VERCEL:
        from src.scheduler_service import init_scheduler
        logger.info("Starting Scheduler...")
        scheduler = init_scheduler()
        scheduler.start()
        app.state.scheduler = scheduler

    yield

    if not IS_VERCEL:
        logger.info("Shutting down Scheduler...")
        try:
            app.state.scheduler.shutdown()
        except Exception as e:
            logger.warning(f"Scheduler shutdown skipped/failed: {e}")
    logger.info("Goodbye.")

def create_app() -> FastAPI:
    app = FastAPI(
        title="Sentinel Dashboard",
        version="1.1.0",
        lifespan=lifespan
    )

    app.mount("/static", StaticFiles(directory=os.path.join(_WEB_DIR, "static")), name="static")
    app.include_router(router)

    return app

app = create_app()
