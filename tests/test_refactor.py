import asyncio
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.scrapers.aicoin import AICoinScraper

async def test_scraper():
    print("Testing AICoinScraper...")
    scraper = AICoinScraper()
    results = await scraper.run()
    
    print(f"\nFound {len(results)} items:")
    for item in results[:3]:
        print(f"- [{item.pub_time}] {item.title} (Source: {item.source}, ID: {item.source_id})")
        print(f"  URL: {item.url}")
        print("---")

if __name__ == "__main__":
    asyncio.run(test_scraper())

