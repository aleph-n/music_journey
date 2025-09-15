import logging
import sys


def setup_logger():
    """Sets up a configured logger instance."""
    logger = logging.getLogger("MusicJourneyLogger")

    # Prevent adding multiple handlers if the function is called more than once
    if logger.hasHandlers():
        return logger

    # Set to DEBUG to capture all levels of messages for troubleshooting
    logger.setLevel(logging.DEBUG)

    # Create a handler to print to the console (stdout)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    # Create a formatter and set it for the handler
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(handler)

    return logger
