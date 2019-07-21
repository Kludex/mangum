import logging


def get_logger() -> logging.Logger:
    logging.basicConfig(
        format="[%(asctime)s] %(message)s",
        level=logging.INFO,
        datefmt="%d-%b-%y %H:%M:%S",
    )
    logger = logging.getLogger("mangum")
    logger.setLevel(logging.INFO)
    return logger
