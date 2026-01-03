import hashlib
import datetime
from typing import List, Any
from playwright.async_api import async_playwright
from src.config import SOURCE_URL, HEADLESS, AICOIN_URL_PREFIX
from src.scrapers.base import BaseScraper, RawNews
from src.logger import setup_logger

logger = setup_logger("AICoin")

class AICoinScraper(BaseScraper):
    def _generate_id(self, title: str, pub_time: datetime.datetime) -> str:
        """生成唯一指纹: MD5(title + pub_time)"""
        raw = f"{title}{pub_time.isoformat()}"
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def _parse_time(self, raw_date: str, raw_time: str) -> datetime.datetime:
        """
        将 '12月29日'/'今天' 和 '17:30' 转换为 datetime 对象
        """
        now = datetime.datetime.now()
        current_year = now.year
        
        # 处理日期
        date_str = raw_date.strip()
        if "今天" in date_str:
            date_obj = now.date()
        else:
            # 假设格式为 "12月29日"
            # 简单处理：移除 "月", "日" -> "12-29"
            try:
                d_str = date_str.replace("月", "-").replace("日", "")
                # 补全年份
                date_obj = datetime.datetime.strptime(f"{current_year}-{d_str}", "%Y-%m-%d").date()
            except ValueError:
                # 如果解析失败，默认当天，避免程序崩溃
                date_obj = now.date()
                
        # 处理时间
        try:
            t_obj = datetime.datetime.strptime(raw_time, "%H:%M").time()
        except ValueError:
            t_obj = now.time()
            
        final_dt = datetime.datetime.combine(date_obj, t_obj)
        return final_dt

    async def run(self) -> List[RawNews]:
        results = []
        logger.info(f"[AICoin] 开始抓取: {SOURCE_URL}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=HEADLESS)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                await page.goto(SOURCE_URL, timeout=60000, wait_until="domcontentloaded")
                await page.wait_for_timeout(5000)
                
                # 1. 获取当前显示的日期 (Sticky Header)
                date_el = await page.query_selector("p.whitespace-nowrap.text-lg.font-medium.text-1")
                date_text = await date_el.inner_text() if date_el else datetime.datetime.now().strftime("%Y-%m-%d")
                
                # 2. 获取快讯条目
                items = await page.query_selector_all("div.relative.flex.gap-4")
                
                # 限制只抓取前 20 条
                for item in items[:20]:
                    try:
                        # 时间
                        time_el = await item.query_selector("div.text-right")
                        time_text = await time_el.inner_text() if time_el else ""
                        time_text = time_text.split('\n')[0].strip()
                        
                        content_card = await item.query_selector("div.flash-card")
                        if not content_card:
                            continue

                        # 标题与链接
                        title_el = await content_card.query_selector("a")
                        title_text = await title_el.inner_text() if title_el else ""
                        href = await title_el.get_attribute("href") if title_el else ""
                        
                        # 展开按钮处理
                        try:
                            expand_btn = await content_card.query_selector("text='展开'")
                            if expand_btn and await expand_btn.is_visible():
                                await expand_btn.click()
                                await page.wait_for_timeout(300)
                        except Exception:
                            pass

                        # 正文
                        body_el = await content_card.query_selector("p[class*='text-2']")
                        body_text = await body_el.inner_text() if body_el else ""
                        
                        if title_text:
                            # 标准化处理
                            pub_time = self._parse_time(date_text, time_text)
                            full_url = AICOIN_URL_PREFIX + href if not href.startswith("http") else href
                            
                            news_item = RawNews(
                                source="aicoin",
                                source_id=self._generate_id(title_text, pub_time),
                                title=title_text,
                                content=body_text,
                                url=full_url,
                                pub_time=pub_time
                            )
                            logger.info(f"[AICoin] 抓取到新闻: {title_text} ({pub_time})")
                            results.append(news_item)
                            
                    except Exception as e_item:
                        logger.error(f"[AICoin] 解析单条数据出错: {e_item}")
                        continue
            
            except Exception as e:
                logger.error(f"[AICoin] 抓取过程发生全局错误: {e}")
            finally:
                if 'context' in locals():
                    await context.close()
                if 'browser' in locals():
                    await browser.close()
                
        logger.info(f"[AICoin] 抓取结束，共获取 {len(results)} 条数据。")
        return results

