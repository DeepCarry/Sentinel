import datetime
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_SUBMITTED
from sqlmodel import Session, select

from src.database import engine
from src.models import NewsFlash, DailyStats, ScanRecord
from src.scrapers.aicoin import AICoinScraper
from src.scrapers.blockbeats import BlockBeatsScraper
from src.filter import get_risk_tags
from src.config import NOTIFICATION_MODE, CRAWL_INTERVAL_MINUTES, NOTIFICATION_INTERVAL_MINUTES
from src.notifier import send_feishu_card, send_feishu_summary
from src.report import run_daily_report, run_weekly_report
from src.logger import setup_logger

# 配置日志
logger = setup_logger("sentinel.scheduler")

async def _run_crawl():
    """并发运行所有爬虫"""
    scrapers = [AICoinScraper(), BlockBeatsScraper()] 
    tasks = [scraper.run() for scraper in scrapers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    flat_results = []
    for res in results:
        if isinstance(res, list):
            flat_results.extend(res)
        else:
            logger.error(f"Scraper task failed: {res}")
    return flat_results

def run_sentinel():
    logger.info(">>> 开始执行监控任务")
    
    # 1. 执行抓取
    try:
        raw_news_list = asyncio.run(_run_crawl())
    except Exception as e:
        logger.error(f"抓取流程异常: {e}")
        return

    if not raw_news_list:
        logger.info("未抓取到任何数据。")
        return

    logger.info(f"抓取到 {len(raw_news_list)} 条原始数据，开始处理...")
    
    # 2. 数据处理入库
    with Session(engine) as session:
        new_count = 0
        skip_count = 0
        push_count = 0
        
        # 获取或创建今日统计对象
        today = datetime.datetime.now().date()
        daily_stats = session.exec(select(DailyStats).where(DailyStats.date == today)).first()
        if not daily_stats:
            try:
                daily_stats = DailyStats(date=today, scanned_count=0)
                session.add(daily_stats)
                # 这里的 commit 可能会在极端并发下冲突，但 scheduler 是单进程/单线程跑（或锁），风险较低
                session.commit() 
                session.refresh(daily_stats)
            except Exception:
                session.rollback()
                daily_stats = session.exec(select(DailyStats).where(DailyStats.date == today)).first()

        # 防御性检查：如果数据库事务异常导致 daily_stats 仍为 None，则本次任务无法计数
        if not daily_stats:
             logger.error("无法获取或创建 DailyStats 对象，跳过计数更新。")
        else:
            # 重新关联到当前 session（防止 refresh/rollback 后 detached）
            daily_stats = session.merge(daily_stats)


        for item in raw_news_list:
            try:
                # 1. 全量查重 (基于 ScanRecord)
                # 即使是噪音数据，只要 ID 出现过，就说明系统已经扫描过，不应重复计数
                scan_stmt = select(ScanRecord).where(ScanRecord.source_id == item.source_id)
                if session.exec(scan_stmt).first():
                    skip_count += 1
                    continue
                
                # 2. 记录新数据 (无论是否高危)
                # 插入扫描历史
                session.add(ScanRecord(source_id=item.source_id))
                # 增加今日扫描计数
                if daily_stats:
                    daily_stats.scanned_count += 1
                    session.add(daily_stats) # 标记为 dirty
                
                # 3. 关键词过滤 (高危判断)
                tags = get_risk_tags(item.title, item.content)
                if not tags:
                    # 虽不是高危，但已计入 scanned，且记录了 source_id 防止未来重复处理
                    continue
                    
                tags_str = ",".join(tags)
                
                # 4. 创建高危记录
                news = NewsFlash(
                    source=item.source,
                    source_id=item.source_id,
                    title=item.title,
                    content=item.content,
                    url=item.url,
                    pub_time=item.pub_time,
                    tags=tags_str,
                    created_at=datetime.datetime.now(),
                    is_pushed=False
                )
                
                # 推送逻辑：根据模式决定是否立即推送
                if NOTIFICATION_MODE == "realtime":
                    # 实时模式：立即推送
                    if send_feishu_card(item.title, item.content, item.url, tags_str, item.pub_time):
                        news.is_pushed = True
                        push_count += 1
                # interval 模式：不立即推送，等待定时汇总任务处理
                # is_pushed 保持 False，由 run_interval_summary() 统一处理
                
                session.add(news)
                new_count += 1
                logger.info(f"[新增] [{item.source}] {item.pub_time.strftime('%H:%M')} | {item.title[:15]}... | 标签: {tags_str}")
                
            except Exception as e:
                logger.error(f"处理单条数据时出错: {e}")
                continue
                
        session.commit()
        logger.info(f"本次任务完成。入库: {new_count}, 实时推送: {push_count}, 过滤/重复: {skip_count}")

def run_interval_summary():
    """
    定时汇总推送任务
    查询最近 N 分钟内未推送的新新闻，汇总后一次性推送
    """
    logger.info(f">>> 开始执行定时汇总推送任务 (模式: interval, 间隔: {NOTIFICATION_INTERVAL_MINUTES}分钟)")
    
    now = datetime.datetime.now()
    time_window_start = now - datetime.timedelta(minutes=NOTIFICATION_INTERVAL_MINUTES)
    
    with Session(engine) as session:
        # 查询最近 N 分钟内未推送的新新闻
        statement = select(NewsFlash).where(
            NewsFlash.is_pushed == False,
            NewsFlash.created_at >= time_window_start,
            NewsFlash.created_at <= now
        ).order_by(NewsFlash.pub_time.desc())
        
        pending_news = session.exec(statement).all()
        
        if not pending_news:
            logger.info(f"时间窗口内 ({time_window_start.strftime('%H:%M')} ~ {now.strftime('%H:%M')}) 无未推送新闻，跳过汇总。")
            return
        
        logger.info(f"查询到 {len(pending_news)} 条未推送新闻，准备汇总推送...")
        
        # 转换为 notifier 需要的格式
        news_items = []
        for news in pending_news:
            news_items.append({
                "title": news.title,
                "url": news.url or "",
                "content": news.content,
                "tags": news.tags
            })
        
        # 发送汇总消息
        title_prefix = f"Sentinel 定时汇总 ({time_window_start.strftime('%H:%M')} ~ {now.strftime('%H:%M')})"
        is_sent = send_feishu_summary(news_items, title_prefix=title_prefix)
        
        if is_sent:
            # 标记为已推送
            update_count = 0
            for news in pending_news:
                db_news = session.get(NewsFlash, news.id)
                if db_news:
                    db_news.is_pushed = True
                    session.add(db_news)
                    update_count += 1
            session.commit()
            logger.info(f"定时汇总推送成功！已推送 {len(pending_news)} 条新闻，并标记为已推送。")
        else:
            logger.warning("定时汇总推送失败 (Webhook 请求异常或未配置)，新闻保持未推送状态。")

def job_listener(event):
    if event.code in (EVENT_JOB_EXECUTED, EVENT_JOB_ERROR):
        pass # APScheduler 默认会打印执行结果，这里不再重复打印

def init_scheduler():
    """初始化并配置调度器"""
    scheduler = BackgroundScheduler()
    scheduler.add_listener(job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    
    # 任务A: 实时监控 (抓取任务，始终运行)
    scheduler.add_job(
        run_sentinel, 
        IntervalTrigger(minutes=CRAWL_INTERVAL_MINUTES), 
        id='monitor_news',
        next_run_time=datetime.datetime.now() # 立即执行一次
    )
    
    # 任务B: 定时汇总推送 (仅在 interval 模式下启用)
    if NOTIFICATION_MODE == "interval":
        scheduler.add_job(
            run_interval_summary,
            IntervalTrigger(minutes=NOTIFICATION_INTERVAL_MINUTES),
            id='interval_summary',
            next_run_time=datetime.datetime.now() + datetime.timedelta(minutes=NOTIFICATION_INTERVAL_MINUTES)  # 延迟启动，等待第一批数据
        )
        logger.info(f"已注册定时汇总推送任务，间隔: {NOTIFICATION_INTERVAL_MINUTES} 分钟")
    else:
        logger.info(f"当前推送模式: {NOTIFICATION_MODE}，定时汇总任务未启用")
    
    # 任务C: 日报推送 (每天 09:00)
    scheduler.add_job(run_daily_report, CronTrigger(hour=9, minute=0), id='daily_report')

    # 任务D: 周报推送 (每周一 09:30)
    scheduler.add_job(run_weekly_report, CronTrigger(day_of_week='mon', hour=9, minute=30), id='weekly_report')
    
    return scheduler
