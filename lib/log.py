import logging.handlers
import time
from logging import Logger
from os.path import join
from typing import Optional

from . import console
from . import path

logger: Optional[logging.Logger]


class LogManager(logging.Formatter, logging.Filter):
    def __init__(self, level: int = logging.DEBUG, fmt=None, date_fmt=None, style='%', validate=True):
        logging.Formatter.__init__(self, fmt, date_fmt, style, validate)
        self.filter_level = level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= self.filter_level


def simple_mgr(fmt: str = "%(asctime)s-%(name)s-%(levelno)s %(message)s",
               date_fmt: str = "%H:%M:%S",
               level: int = logging.INFO, ) -> LogManager:
    return LogManager(level=level, fmt=fmt, date_fmt=date_fmt)


def verbose_mgr(fmt: str = "[%(asctime)s][%(name)s-%(levelname)s] %(message)s",
                date_fmt: str = "%Y-%m-%d %H:%M:%S",
                level: int = logging.DEBUG, ) -> LogManager:
    return LogManager(level=level, fmt=fmt, date_fmt=date_fmt)


def create_logger(con: console.Console,
                  simple: LogManager = simple_mgr(),
                  verbose: LogManager = verbose_mgr(),
                  ) -> Logger:
    global logger
    logger = logging.getLogger("")
    logger.level = logging.DEBUG
    date = time.strftime("%Y-%m-%d")
    f_handler = logging.FileHandler(filename=join(path.log, f"{date}.log"), mode="a", encoding="utf-8")
    q_handler = logging.handlers.QueueHandler(con.log_queue)
    f_handler.setFormatter(simple)
    f_handler.addFilter(simple)
    q_handler.setFormatter(verbose)
    q_handler.addFilter(verbose)
    logger.addHandler(f_handler)
    logger.addHandler(q_handler)

    return logger