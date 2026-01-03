from typing import Optional
from datetime import datetime, date as dt_date
from sqlmodel import Field, SQLModel

class NewsFlash(SQLModel, table=True):
    """
    快讯数据模型 - 映射到数据库表 'newsflash'
    """
    __tablename__ = "newsflash"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 来源信息
    source: str = Field(default="aicoin", description="数据来源 (e.g., 'aicoin', 'blockbeats')")
    
    # 核心去重字段
    source_id: str = Field(index=True, unique=True, description="来源原始ID或Hash指纹")
    
    # 内容字段
    title: str = Field(index=True)
    content: str
    url: Optional[str] = None
    
    # 时间字段
    pub_time: datetime = Field(index=True, description="新闻发布时间")
    created_at: datetime = Field(default_factory=datetime.now, description="系统抓取时间")
    updated_at: datetime = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now}, description="系统更新时间")
    
    # 智能标签
    tags: str = Field(default="", description="触发的关键词标签，如 '安全,黑客'")
    
    # 状态标记
    is_pushed: bool = Field(default=False, description="是否已通过Webhook推送")
    in_daily_report: bool = Field(default=False, description="是否已计入日报")
    in_weekly_report: bool = Field(default=False, description="是否已计入周报")

class Report(SQLModel, table=True):
    """
    报表归档模型 - 映射到数据库表 'reports'
    """
    __tablename__ = "reports"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 报表元数据
    type: str = Field(description="报表类型: 'daily' 或 'weekly'")
    period_start: datetime = Field(description="统计周期开始时间")
    period_end: datetime = Field(description="统计周期结束时间")
    
    # 报表内容
    content_html: str = Field(description="报表HTML内容")
    
    # 生成信息
    created_at: datetime = Field(default_factory=datetime.now, description="生成时间")

class DailyStats(SQLModel, table=True):
    """
    每日统计模型 - 用于记录每日抓取总量(含噪音)
    """
    __tablename__ = "daily_stats"

    id: Optional[int] = Field(default=None, primary_key=True)
    date: dt_date = Field(index=True, unique=True, description="统计日期 (yyyy-mm-dd)")
    scanned_count: int = Field(default=0, description="当日经过去重的原始抓取总数")
    updated_at: datetime = Field(default_factory=datetime.now, sa_column_kwargs={"onupdate": datetime.now})

class ScanRecord(SQLModel, table=True):
    """
    扫描历史记录 - 仅用于全量去重 (ID 集合)
    """
    __tablename__ = "scan_record"

    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: str = Field(index=True, unique=True, description="来源原始ID")
    created_at: datetime = Field(default_factory=datetime.now)
