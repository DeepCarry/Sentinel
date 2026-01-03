import logging
import sys
import os
from logging.handlers import RotatingFileHandler

# 创建 logs 目录
os.makedirs("logs", exist_ok=True)

def setup_logger(name: str) -> logging.Logger:
    """
    配置并返回一个标准的 logger 实例
    """
    logger = logging.getLogger(name)
    
    # 如果 logger 已经有 handler，说明已被配置过，直接返回
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.INFO)
    
    # 格式
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 1. 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 2. 文件输出 (按大小轮转，最大 5MB，保留 3 个备份)
    file_handler = RotatingFileHandler(
        filename="logs/sentinel.log",
        maxBytes=5*1024*1024,
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

