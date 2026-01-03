from sqlmodel import create_engine, SQLModel
from src.config import SQLITE_URL

# 数据库引擎
engine = create_engine(SQLITE_URL)

def init_db():
    """初始化数据库表结构"""
    # 延迟导入以避免循环依赖
    from src.models import NewsFlash, Report, DailyStats, ScanRecord
    SQLModel.metadata.create_all(engine)

