import logging
import sys
import time

from src.notifier import send_feishu_card


class FeishuErrorHandler(logging.Handler):
    def __init__(self, min_interval_seconds: int = 60) -> None:
        super().__init__(level=logging.ERROR)
        self.min_interval_seconds = min_interval_seconds
        self._last_sent: dict[str, float] = {}

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno < logging.ERROR:
            return

        try:
            key = f"{record.name}:{record.getMessage()}"
            now = time.time()
            last = self._last_sent.get(key)
            if last is not None and now - last < self.min_interval_seconds:
                return

            self._last_sent[key] = now

            message = self.format(record)
            title = f"{record.levelname} - {record.name}"

            send_feishu_card(
                title=title,
                content=message,
                url="",
                tags="系统错误",
            )
        except Exception:
            self.handleError(record)


def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    feishu_handler = FeishuErrorHandler()
    feishu_handler.setFormatter(formatter)
    logger.addHandler(feishu_handler)

    return logger
