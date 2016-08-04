import logging


def make_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s [%(levelname)-5.5s]  %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    return logger

# this is a common, global logger instance for dividebatur
logger = make_logger("dividebatur")
logger.setLevel(logging.INFO)
