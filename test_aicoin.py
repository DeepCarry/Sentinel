import asyncio
import datetime
from src.scrapers.aicoin import AICoinScraper

async def test_scraper():
    print("="*60)
    print("Testing AICoinScraper...")
    print("="*60)
    
    scraper = AICoinScraper()
    results = await scraper.run()
    
    if not results:
        print("❌ 未抓取到任何数据！请检查选择器或网络连接。")
        return

    print(f"\n✅ 抓取完成！共找到 {len(results)} 条快讯\n")
    print("前 5 条快讯详情：")
    print("-" * 60)
    
    for i, news in enumerate(results[:5], 1):
        print(f"\n【快讯 {i}】")
        print(f"标题: {news.title}")
        print(f"发布时间: {news.pub_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"来源: {news.source}")
        print(f"Source ID: {news.source_id}")
        print(f"URL: {news.url}")
        print(f"内容预览: {news.content[:100]}..." if news.content else "无内容")
        print("-" * 60)

if __name__ == "__main__":
    asyncio.run(test_scraper())

