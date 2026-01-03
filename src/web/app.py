from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from src.database import init_db
from src.web.routes import router
from src.scheduler_service import init_scheduler
from src.logger import setup_logger

# 配置日志
logger = setup_logger("sentinel.web")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 生命周期管理
    """
    logger.info("Initializing Database...")
    init_db()
    
    logger.info("Starting Scheduler...")
    scheduler = init_scheduler()
    scheduler.start()
    # 将调度器实例挂载到 app.state 以便在路由中访问
    app.state.scheduler = scheduler
    
    yield
    
    logger.info("Shutting down Scheduler...")
    # 调试/开发时 scheduler 可能未 start()，直接 shutdown 会抛 SchedulerNotRunningError
    try:
        scheduler.shutdown()
    except Exception as e:
        logger.warning(f"Scheduler shutdown skipped/failed: {e}")
    logger.info("Goodbye.")

def create_app() -> FastAPI:
    app = FastAPI(
        title="Sentinel Dashboard",
        version="1.1.0",
        lifespan=lifespan
    )
    
    # 挂载静态文件目录
    app.mount("/static", StaticFiles(directory="src/web/static"), name="static")
    
    # 注册路由
    app.include_router(router)
    
    return app

app = create_app()
