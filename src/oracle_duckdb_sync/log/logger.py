import logging
import sys


def setup_logger(name: str, log_file: str = "sync.log", level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove old handlers first to prevent accumulation
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 콘솔 출력
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 파일 출력 (즉시 flush)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    # Force flush after every log
    file_handler.flush = lambda: file_handler.stream.flush() if file_handler.stream else None
    logger.addHandler(file_handler)

    return logger


def cleanup_logger(logger):
    """Close all handlers and remove them"""
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
