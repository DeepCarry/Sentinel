import asyncio
import sys
import os

# 确保 src 目录在 python path 中
sys.path.append(os.getcwd())

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

