import datetime
import sys
from pathlib import Path
from sqlmodel import Session, select

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import engine, init_db
from src.models import NewsFlash
from src.report import run_daily_report, run_weekly_report

def setup_test_data():
    """确保有一条最近的新闻用于测试"""
    with Session(engine) as session:
        # 检查是否有最近24小时的数据
        now = datetime.datetime.now()
        yesterday = now - datetime.timedelta(hours=23)
        
        statement = select(NewsFlash).where(NewsFlash.pub_time >= yesterday)
        existing = session.exec(statement).first()
        
        if not existing:
            print(">>> 数据库中无近期数据，正在生成一条测试数据...")
            test_news = NewsFlash(
                source_id=f"test_id_{int(now.timestamp())}",
                title="[测试] 比特币突破10万美元大关",
                content="这是一个用于测试日报功能的模拟新闻内容。比特币今日持续上涨...",
                url="https://www.aicoin.com/article/test",
                pub_time=now - datetime.timedelta(hours=2), # 2小时前
                created_at=now,
                tags="行情,测试",
                is_pushed=False
            )
            session.add(test_news)
            session.commit()
            print(f">>> 测试数据已插入: {test_news.title}")
        else:
            print(f">>> 发现现有数据: {existing.title}，无需生成。")

def main():
    print("=== 开始测试报表模块 ===")
    
    # 1. 确保数据库已初始化
    init_db()
    
    # 2. 准备数据
    setup_test_data()
    
    # 3. 测试日报
    print("\n--- 测试日报 (Daily Report) ---")
    try:
        run_daily_report()
    except Exception as e:
        print(f"!!! 日报测试失败: {e}")
        import traceback
        traceback.print_exc()

    # 4. 测试周报
    print("\n--- 测试周报 (Weekly Report) ---")
    try:
        run_weekly_report()
    except Exception as e:
        print(f"!!! 周报测试失败: {e}")
        import traceback
        traceback.print_exc()
        
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    main()

