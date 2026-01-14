import os
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()

# --- 基础配置 ---
# 飞书 Webhook 地址 (优先从环境变量获取，否则使用默认值)
FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "https://open.larksuite.com/open-apis/bot/v2/hook/834f69dc-41e0-466c-92ff-7f4285a59942")

# 数据库路径 (存放在 data 目录下)
DB_PATH = "data/sentinel.db"
SQLITE_URL = f"sqlite:///{DB_PATH}"

# 抓取源
SOURCE_URL = "https://www.aicoin.com/zh-Hans/news-flash"
AICOIN_URL_PREFIX = "https://www.aicoin.com/zh-Hans"

# --- 监控策略 ---

# 1. 白名单 (Whitelist Keywords)
# 只要命中其中任意一个，即视为潜在目标
KEYWORDS_SECURITY = [
    "KYT", "风控", "安全", "盗币", "被盗", "黑客", "攻击", "漏洞", 
    "私钥", "泄露", "钓鱼", "Rug", "跑路", "赔偿", "异动"
]

KEYWORDS_COMPLIANCE = [
    "监管", "合规", "洗钱", "反洗钱", "涉嫌", "非法", "制裁", "SEC", 
    "FCA", "SFC", "证监会", "司法部", "起诉", "罚款", "牌照", "实名", "冻结", "立法"
]

KEYWORDS_MACRO = [
    "美联储", "利率", "加息", "降息", "CPI", "通胀", "鲍威尔"
]

# 合并所有监控词
ALL_KEYWORDS = KEYWORDS_SECURITY + KEYWORDS_COMPLIANCE + KEYWORDS_MACRO

# 2. 黑名单 (Blacklist Keywords)
# 即使命中白名单，如果包含以下词汇，直接丢弃 (过滤噪音)
IGNORE_WORDS = [
    "赞助", "广告", "推广", "空投", "抽奖", "赠送", "邀请", "返佣", 
    "峰会预告", "早报", "晚报", "行情分析", "涨幅", "跌幅", "狂送", "直播"
]

# --- 爬虫配置 ---
CRAWL_INTERVAL_MINUTES = 2  # 抓取间隔 (分钟)
HEADLESS = True  # 是否使用无头模式 (不显示浏览器窗口)

# --- 通知策略配置 ---
# 推送模式: 'realtime' (实时) 或 'interval' (定时汇总)
NOTIFICATION_MODE = "realtime"

# 定时汇总间隔 (分钟)，仅在 mode='interval' 时生效
# 建议设为 60 分钟，避免信息轰炸
NOTIFICATION_INTERVAL_MINUTES = 60
