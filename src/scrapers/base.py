from abc import ABC, abstractmethod
from typing import List
from datetime import datetime
from pydantic import BaseModel

# RawNews 表示“原始新闻”对象，用于标准化爬虫抓取到的单条新闻快讯的结构
class RawNews(BaseModel):
    source: str
    source_id: str
    title: str
    content: str
    url: str
    pub_time: datetime

# ABC 代表 "Abstract Base Class"，即抽象基类，用于定义接口和强制派生类实现必须的方法
class BaseScraper(ABC):
    @abstractmethod
    async def run(self) -> List[RawNews]:
        """
        运行抓取逻辑，返回标准化的原始新闻列表
        """
        pass

