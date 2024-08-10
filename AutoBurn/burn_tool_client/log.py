#!/usr/bin/env python3

import logging


class ColoredFormatter(logging.Formatter):
    COLORS: dict[str, str] = {
        'NOTSET': '\033[97m',
        'DEBUG': '\033[94m',
        'INFO': '\033[92m',
        'WARNING': '\033[93m',
        'ERROR': '\033[91m',
        'CRITICAL': '\033[95m'
    }
    RESET = '\033[0m'

    def format(self, record) -> str:
        log_color = self.COLORS.get(record.levelname, '')
        reset_color = self.RESET
        record.msg = log_color + super().format(record) + reset_color
        return record.msg


def logging_setup(level) -> None:
    logger: logging.Logger = logging.getLogger()

    handler = logging.StreamHandler()
    formatter = ColoredFormatter('%(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level=level)
