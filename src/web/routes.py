import os
import re
import asyncio
from collections import deque
from pathlib import Path
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, desc
from sqlalchemy import func, or_
from datetime import datetime

from src.database import engine
from src.models import NewsFlash, Report, DailyStats, ScanRecord
from src.config import NOTIFICATION_MODE
from src.logger import setup_logger

logger = setup_logger("sentinel.web.routes")

router = APIRouter()

_WEB_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(_WEB_DIR, "templates"))
_PROJECT_ROOT = Path(_WEB_DIR).resolve().parents[1]
_LOG_FILE = _PROJECT_ROOT / "logs" / "sentinel.log"
_LEGACY_LOG_FILE = _PROJECT_ROOT / "logs" / "startup.log"
_ERROR_LOG_PATTERN = re.compile(r"\[(ERROR|WARNING|CRITICAL)\]")

def get_session():
    with Session(engine) as session:
        yield session

def _resolve_log_file() -> Path | None:
    if _LOG_FILE.exists():
        return _LOG_FILE
    if _LEGACY_LOG_FILE.exists():
        return _LEGACY_LOG_FILE
    return None

def _is_error_line(line: str) -> bool:
    return bool(_ERROR_LOG_PATTERN.search(line))

def _read_last_lines(log_file: Path, limit: int) -> list[str]:
    with log_file.open("r", encoding="utf-8", errors="replace") as f:
        return list(deque(f, maxlen=limit))

def _to_sse(line: str) -> str:
    chunks = line.rstrip("\n").splitlines() or [""]
    return "".join(f"data: {chunk}\n" for chunk in chunks) + "\n"

@router.get("/")
async def dashboard(request: Request, session: Session = Depends(get_session)):
    """
    仪表盘首页: 显示今日统计和最新快讯
    """
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    
    # 统计今日数据
    # 1. 获取今日抓取总量 (Scanned Count) - 包含噪音
    daily_stats = session.exec(
        select(DailyStats).where(DailyStats.date == today_start.date())
    ).first()
    today_scanned_count = daily_stats.scanned_count if daily_stats else 0

    # 2. 获取今日高危数量 (Risk Count) - 实际入库数量
    # 既然现在 NewsFlash 里存的都是高危，直接 count 即可
    # (为了兼容旧数据或防御性编程，依然保留 tags != "" 的条件)
    today_risks_count = session.exec(
        select(func.count(NewsFlash.id))
        .where(NewsFlash.created_at >= today_start)
        .where(NewsFlash.tags != "")
    ).one()

    # 3. 获取累计抓取与匹配 (系统启动至今)
    total_scanned_count = session.exec(
        select(func.count(ScanRecord.id))
    ).one()
    total_matched_count = session.exec(
        select(func.count(NewsFlash.id))
    ).one()
    
    # 获取最新 10 条高危快讯 (有标签的)
    recent_risks = session.exec(
        select(NewsFlash)
        .where(NewsFlash.tags != "")
        .order_by(desc(NewsFlash.pub_time))
        .limit(10)
    ).all()
    
    # 获取系统状态
    scheduler = getattr(request.app.state, "scheduler", None)
    # APScheduler running 属性
    system_status = scheduler.running if scheduler else False
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "today_count": today_scanned_count,
        "today_risks": today_risks_count,
        "total_scanned": total_scanned_count,
        "total_matched": total_matched_count,
        "recent_risks": recent_risks,
        "last_update": now.strftime("%Y-%m-%d %H:%M:%S"),
        "system_status": system_status
    })

@router.get("/news")
async def news_list(
    request: Request, 
    page: int = 1, 
    source: str = Query(None),
    tag: str = Query(None),
    keyword: str = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    session: Session = Depends(get_session)
):
    """
    快讯列表页: 支持分页和筛选
    """
    PAGE_SIZE = 20
    offset = (page - 1) * PAGE_SIZE

    def _parse_date_like(s: str) -> datetime | None:
        """
        解析前端日期参数，兼容常见格式。
        - HTML <input type="date">: YYYY-MM-DD
        - 兜底: ISO 8601 (YYYY-MM-DDTHH:MM[:SS[.ffffff]][Z])
        """
        if not s:
            return None
        s = s.strip()
        if not s:
            return None
        # 1) 最常见格式
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        # 2) 兼容更完整的 ISO（可能带毫秒/微秒、可能带 Z）
        try:
            # Python datetime.fromisoformat 不支持末尾 Z
            s2 = s[:-1] if s.endswith("Z") else s
            return datetime.fromisoformat(s2)
        except ValueError:
            return None
    
    query = select(NewsFlash).order_by(desc(NewsFlash.pub_time))
    
    if source:
        query = query.where(NewsFlash.source == source)
    if tag and tag.strip():
        # 使用 SQLAlchemy 的 like 函数确保在 SQLite 中正常工作（不区分大小写）
        tag_clean = tag.strip()
        query = query.where(func.lower(NewsFlash.tags).like(f"%{tag_clean.lower()}%"))
    if keyword and keyword.strip():
        # 关键词：更符合直觉的行为是 “标题或正文” 命中即可
        keyword_clean = keyword.strip()
        kw = f"%{keyword_clean.lower()}%"
        query = query.where(
            or_(
                func.lower(NewsFlash.title).like(kw),
                func.lower(NewsFlash.content).like(kw),
            )
        )
    
    if start_date:
        start_dt = _parse_date_like(start_date)
        if start_dt is None:
            logger.warning(f"Invalid start_date ignored: {start_date!r}, url={request.url}")
        else:
            query = query.where(NewsFlash.pub_time >= start_dt)

    if end_date:
        end_dt = _parse_date_like(end_date)
        if end_dt is None:
            logger.warning(f"Invalid end_date ignored: {end_date!r}, url={request.url}")
        else:
            # Set to end of day（如果只传了日期，兜底到当天结束）
            if end_dt.hour == 0 and end_dt.minute == 0 and end_dt.second == 0 and end_dt.microsecond == 0:
                end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.where(NewsFlash.pub_time <= end_dt)

    # 关键诊断日志：确认参数是否传到后端，以及 SQL 条件是否拼上
    try:
        compiled = query.compile(engine, compile_kwargs={"literal_binds": True})
        sql_preview = str(compiled)
    except Exception:
        sql_preview = str(query)
    logger.info(
        "news_list filters: "
        f"page={page}, source={source!r}, tag={tag!r}, keyword={keyword!r}, "
        f"start_date={start_date!r}, end_date={end_date!r}, url={request.url}, sql={sql_preview}"
    )
        
    # 计算总数 (用于分页)
    # 注意: SQLModel/SQLAlchemy 计算 count 比较繁琐，这里简化处理，或者暂不显示总页数
    # 为了性能，生产环境应该单独 count，这里简单查所有可能比较慢
    # total = len(session.exec(query).all()) 
    
    results = session.exec(query.offset(offset).limit(PAGE_SIZE)).all()
    
    return templates.TemplateResponse("news_list.html", {
        "request": request,
        "news_list": results,
        "page": page,
        "source": source,
        "tag": tag,
        "keyword": keyword,
        "start_date": start_date,
        "end_date": end_date
    })

@router.get("/news/{news_id}")
async def news_detail(request: Request, news_id: int, session: Session = Depends(get_session)):
    news = session.get(NewsFlash, news_id)
    return templates.TemplateResponse("news_detail.html", {
        "request": request,
        "news": news
    })

@router.get("/reports")
async def report_list(request: Request, session: Session = Depends(get_session)):
    """
    历史报表归档列表
    """
    reports = session.exec(select(Report).order_by(desc(Report.created_at)).limit(50)).all()
    return templates.TemplateResponse("report_list.html", {
        "request": request,
        "reports": reports
    })

@router.get("/reports/{report_id}")
async def report_detail(report_id: int, session: Session = Depends(get_session)):
    """
    渲染具体的报表 HTML
    """
    report = session.get(Report, report_id)
    if not report:
        return "Report not found"
    # 直接返回 HTML 内容
    return HTMLResponse(content=report.content_html)

@router.get("/logs")
async def logs_page(request: Request, tab: str = Query("all")):
    active_tab = "error" if tab == "error" else "all"
    return templates.TemplateResponse("logs.html", {
        "request": request,
        "tab": active_tab,
    })

@router.get("/api/logs/stream")
async def logs_stream(
    request: Request,
    tab: str = Query("all"),
    lines: int = Query(100, ge=20, le=500),
):
    active_tab = "error" if tab == "error" else "all"

    async def event_generator():
        current_log = _resolve_log_file()
        yield _to_sse(f"[system] 已连接日志流，当前筛选: {active_tab}")
        if current_log is None:
            yield _to_sse("[system] 日志文件不存在，等待服务写入...")
            while not await request.is_disconnected():
                await asyncio.sleep(1.5)
                current_log = _resolve_log_file()
                if current_log is not None:
                    yield _to_sse(f"[system] 已检测到日志文件: {current_log.name}")
                    break
            if current_log is None:
                return

        emitted = 0
        for line in _read_last_lines(current_log, lines):
            if active_tab == "error" and not _is_error_line(line):
                continue
            yield _to_sse(line)
            emitted += 1

        if emitted == 0 and active_tab == "error":
            yield _to_sse("[system] 暂无错误日志，等待新事件...")

        log_fp = current_log.open("r", encoding="utf-8", errors="replace")
        log_fp.seek(0, os.SEEK_END)
        last_position = log_fp.tell()
        try:
            while not await request.is_disconnected():
                latest_log = _resolve_log_file()
                if latest_log is None:
                    await asyncio.sleep(1.0)
                    continue

                if latest_log != current_log:
                    log_fp.close()
                    current_log = latest_log
                    log_fp = current_log.open("r", encoding="utf-8", errors="replace")
                    log_fp.seek(0, os.SEEK_END)
                    last_position = log_fp.tell()
                    yield _to_sse(f"[system] 日志文件已切换: {current_log.name}")

                line = log_fp.readline()
                if line:
                    last_position = log_fp.tell()
                    if active_tab == "error" and not _is_error_line(line):
                        continue
                    yield _to_sse(line)
                    continue

                try:
                    file_size = current_log.stat().st_size
                except OSError:
                    file_size = last_position

                if file_size < last_position:
                    log_fp.close()
                    log_fp = current_log.open("r", encoding="utf-8", errors="replace")
                    last_position = 0

                await asyncio.sleep(0.8)
        finally:
            log_fp.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@router.get("/health/check")
async def health_check():
    """
    健康检查接口
    """
    return {"status": "ok"}
