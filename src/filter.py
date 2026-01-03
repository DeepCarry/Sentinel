from typing import List
from src.config import (
    KEYWORDS_SECURITY, 
    KEYWORDS_COMPLIANCE, 
    KEYWORDS_MACRO, 
    IGNORE_WORDS
)

def get_risk_tags(title: str, content: str) -> List[str]:
    """
    根据标题和正文判断是否命中监控关键词。
    
    Returns:
        List[str]: 命中的标签列表 (如 ['安全', '合规'])。
                   如果命中黑名单或未命中白名单，返回空列表。
    """
    # 拼接标题和内容进行统一检索
    full_text = f"{title} {content}".lower()
    
    # 1. 黑名单检查 (优先级最高)
    # 如果包含任意黑名单词汇，直接忽略，不生成任何标签
    for ignore_word in IGNORE_WORDS:
        if ignore_word.lower() in full_text:
            return []
            
    matched_tags = []
    
    # 2. 白名单检查 - 安全类
    for kw in KEYWORDS_SECURITY:
        if kw.lower() in full_text:
            matched_tags.append("安全")
            break # 同一类别命中一个词即可
            
    # 3. 白名单检查 - 合规类
    for kw in KEYWORDS_COMPLIANCE:
        if kw.lower() in full_text:
            matched_tags.append("合规")
            break
            
    # 4. 白名单检查 - 宏观类
    for kw in KEYWORDS_MACRO:
        if kw.lower() in full_text:
            matched_tags.append("宏观")
            break
            
    return matched_tags

