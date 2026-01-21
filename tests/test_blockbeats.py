import asyncio
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.scrapers.blockbeats import BlockBeatsScraper

async def test_blockbeats_scraper():
    """测试 BlockBeats 爬虫"""
    print("=" * 60)
    print("Testing BlockBeatsScraper...")
    print("=" * 60)
    
    scraper = BlockBeatsScraper()
    results = await scraper.run()
    
    print(f"\n✅ 抓取完成！共找到 {len(results)} 条重要快讯\n")
    
    if results:
        print("前 5 条快讯详情：")
        print("-" * 60)
        for i, item in enumerate(results[:5], 1):
            print(f"\n【快讯 {i}】")
            print(f"标题: {item.title}")
            print(f"发布时间: {item.pub_time.strftime('%Y-%m-%d %H:%M')}")
            print(f"来源: {item.source}")
            print(f"Source ID: {item.source_id}")
            print(f"URL: {item.url or '无链接'}")
            print(f"内容预览: {item.content[:200]}..." if len(item.content) > 200 else f"内容: {item.content}")
            print("-" * 60)
    else:
        print("⚠️  未抓取到任何数据，请检查：")
        print("  1. 网络连接是否正常")
        print("  2. 页面结构是否发生变化")
        print("  3. 是否有重要快讯数据")

if __name__ == "__main__":
    asyncio.run(test_blockbeats_scraper())

