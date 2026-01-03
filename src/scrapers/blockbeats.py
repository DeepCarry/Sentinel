import hashlib
import datetime
from typing import List
from playwright.async_api import async_playwright
from src.config import HEADLESS
from src.scrapers.base import BaseScraper, RawNews
from src.logger import setup_logger

logger = setup_logger("sentinel.scrapers.blockbeats")

class BlockBeatsScraper(BaseScraper):
    """BlockBeats 快讯爬虫 - 只爬取重要快讯"""
    
    BLOCKBEATS_URL = "https://www.theblockbeats.info/newsflash"
    BLOCKBEATS_URL_PREFIX = "https://www.theblockbeats.info"
    
    def _generate_id(self, title: str, pub_time: datetime.datetime) -> str:
        """生成唯一指纹: MD5(title + pub_time)"""
        raw = f"{title}{pub_time.isoformat()}"
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def _parse_time(self, time_str: str) -> datetime.datetime:
        """
        将时间字符串（如 '10:46'）转换为 datetime 对象
        使用当前日期
        """
        now = datetime.datetime.now()
        try:
            time_obj = datetime.datetime.strptime(time_str.strip(), "%H:%M").time()
            # 使用当前日期，如果时间大于当前时间，则认为是昨天的
            pub_dt = datetime.datetime.combine(now.date(), time_obj)
            if pub_dt > now:
                # 如果解析出的时间大于当前时间，则认为是昨天的
                pub_dt = pub_dt - datetime.timedelta(days=1)
            return pub_dt
        except ValueError:
            # 如果解析失败，使用当前时间
            return now

    async def run(self) -> List[RawNews]:
        results = []
        logger.info(f"[BlockBeats] 开始抓取: {self.BLOCKBEATS_URL}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=HEADLESS)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            try:
                await page.goto(self.BLOCKBEATS_URL, timeout=60000, wait_until="domcontentloaded")
                await page.wait_for_timeout(5000)
                
                # 确保"重要快讯"复选框被选中
                try:
                    # 先找到包含文本的 label
                    checkbox_label = await page.wait_for_selector('label.el-checkbox:has-text("重要快讯")', timeout=5000)
                    if checkbox_label:
                        # 获取实际的 input 元素来检查状态
                        input_el = await checkbox_label.query_selector('input.el-checkbox__original')
                        if input_el:
                            is_checked = await input_el.is_checked()
                            if not is_checked:
                                # 点击可视化的 checkbox 元素 (span.el-checkbox__inner)
                                # input 元素通常是隐藏的或覆盖的，不能直接点击
                                visual_checkbox = await checkbox_label.query_selector('.el-checkbox__inner')
                                if visual_checkbox:
                                    await visual_checkbox.click()
                                else:
                                    # 如果找不到 visual element，尝试点击 label
                                    await checkbox_label.click()
                                await page.wait_for_timeout(2000)  # 等待页面更新
                except Exception as e:
                    logger.error(f"[BlockBeats] 设置重要快讯复选框时出错: {e}")
                
                # 获取快讯列表容器
                flash_list = await page.query_selector('div.flash-list')
                if not flash_list:
                    logger.warning("[BlockBeats] 未找到快讯列表容器")
                    return results
                
                # 获取所有快讯条目
                items = await flash_list.query_selector_all('div.news-flash-wrapper')
                
                for item in items:
                    try:      
                        # 获取时间（在 h2 > a 的第一个文本节点）
                        title_link = await item.query_selector('h2 a.news-flash-title')
                        if not title_link:
                            continue
                        
                        # 获取时间文本（第一个文本节点，在 img 之前）
                        time_text = ""
                        try:
                            # 使用 evaluate 获取第一个文本节点
                            time_text = await title_link.evaluate("""
                                (el) => {
                                    for (let node of el.childNodes) {
                                        if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
                                            return node.textContent.trim();
                                        }
                                    }
                                    return '';
                                }
                            """)
                            # 如果上面没获取到，尝试从 inner_text 中提取
                            if not time_text:
                                link_text = await title_link.inner_text()
                                # 时间通常在开头，格式如 "10:46"
                                parts = link_text.split('\n')
                                if parts:
                                    time_text = parts[0].strip()
                        except Exception as e:
                            logger.warning(f"[BlockBeats] 提取时间时出错: {e}")
                            pass
                        
                        if not time_text:
                            continue
                        
                        # 获取标题
                        title_el = await item.query_selector('div.news-flash-title-text')
                        title_text = await title_el.inner_text() if title_el else ""
                        if not title_text:
                            continue
                        
                        # 获取内容
                        content_el = await item.query_selector('div.news-flash-item-content')
                        if not content_el:
                            continue
                        
                        # 获取所有段落文本
                        paragraphs = await content_el.query_selector_all('p')
                        content_parts = []
                        for p in paragraphs:
                            p_text = await p.inner_text()
                            if p_text.strip():
                                content_parts.append(p_text.strip())
                        
                        # 移除原文链接文本（如果有）
                        content_text = '\n\n'.join(content_parts)
                        
                        # 获取原文链接
                        original_link = await content_el.query_selector('a[style*="color: #4065F6"]')
                        url = ""
                        if original_link:
                            href = await original_link.get_attribute('href')
                            if href:
                                # 处理相对路径和绝对路径
                                if href.startswith('http'):
                                    url = href
                                else:
                                    url = self.BLOCKBEATS_URL_PREFIX + href
                        
                        # 如果没有找到原文链接，尝试从标题链接获取
                        if not url:
                            href = await title_link.get_attribute('href')
                            if href:
                                if href.startswith('http'):
                                    url = href
                                else:
                                    url = self.BLOCKBEATS_URL_PREFIX + href
                        
                        # 解析发布时间
                        pub_time = self._parse_time(time_text)
                        
                        news_item = RawNews(
                            source="blockbeats",
                            source_id=self._generate_id(title_text, pub_time),
                            title=title_text,
                            content=content_text,
                            url=url if url else None,
                            pub_time=pub_time
                        )
                        logger.info(f"[BlockBeats] 抓取到快讯: {title_text} ({pub_time})")
                        results.append(news_item)
                        
                    except Exception as e_item:
                        logger.error(f"[BlockBeats] 解析单条数据出错: {e_item}")
                        continue
            
            except Exception as e:
                logger.error(f"[BlockBeats] 抓取过程发生全局错误: {e}")
            finally:
                if 'context' in locals():
                    await context.close()
                if 'browser' in locals():
                    await browser.close()
                
        logger.info(f"[BlockBeats] 抓取结束，共获取 {len(results)} 条重要快讯。")
        return results

