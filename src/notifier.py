import requests
import datetime
from typing import List, Dict
from src.config import FEISHU_WEBHOOK_URL

def send_feishu_card(title: str, content: str, url: str, tags: str, pub_time: datetime.datetime = None) -> bool:
    """
    发送单条富文本卡片消息 (实时模式)
    """
    if not FEISHU_WEBHOOK_URL:
        # 开发环境下如果没有配置 webhook，仅打印日志
        print(f"[Notifier] 未配置 Webhook，模拟发送: {title}")
        return False

    # 确定显示的时间
    display_time = pub_time.strftime('%Y-%m-%d %H:%M') if pub_time else datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

    # 构造卡片颜色，根据标签简单区分
    header_color = "blue"
    if "安全" in tags:
        header_color = "red"
    elif "合规" in tags:
        header_color = "orange"

    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": header_color,
                "title": {
                    "content": f"🚨 Sentinel 监控预警: {title}",
                    "tag": "plain_text"
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": f"**标签:** {tags}\n**时间:** {display_time}\n\n{content}",
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "content": "查看详情",
                                "tag": "plain_text"
                            },
                            "url": url,
                            "type": "primary"
                        }
                    ]
                }
            ]
        }
    }

    try:
        resp = requests.post(FEISHU_WEBHOOK_URL, json=payload)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 0:
            print(f"飞书消息推送成功: {title}")
            return True
        else:
            print(f"飞书推送失败: {result}")
            return False
    except Exception as e:
        print(f"飞书推送请求异常: {e}")
        return False

def send_feishu_summary(news_items: List[Dict], title_prefix: str = "Sentinel 周期汇总") -> bool:
    """
    发送汇总消息 (定时模式)
    """
    if not news_items:
        return False

    # 构造消息体
    content_lines = []
    for idx, item in enumerate(news_items, 1):
        content_preview = item['content']
        if len(content_preview) > 150:
            content_preview = content_preview[:150] + "..."
        
        line = f"{idx}. **[{item['tags']}]** [{item['title']}]({item['url']})\n   - {content_preview}"
        content_lines.append(line)
    
    full_content = "\n\n".join(content_lines)

    if not FEISHU_WEBHOOK_URL:
        print(f"[Notifier] 未配置 Webhook，模拟发送汇总消息 ({len(news_items)} 条):")
        print(full_content)
        return False

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "template": "turquoise",
                "title": {
                    "content": f"📋 {title_prefix} ({len(news_items)}条)",
                    "tag": "plain_text"
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": full_content,
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"统计时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        }
                    ]
                }
            ]
        }
    }

    try:
        resp = requests.post(FEISHU_WEBHOOK_URL, json=payload)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"汇总推送异常: {e}")
        return False

