import logging
from copy import copy

from colorama import Fore, Style


class ColorFormatter(logging.Formatter):
    # Define colors for each log level
    LOG_COLORS: dict[int, str] = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA + Style.BRIGHT,
    }

    def format(self, record: logging.LogRecord) -> str:
        colored_record = copy(record)
        # Get the color based on the log level
        log_color = self.LOG_COLORS.get(colored_record.levelno, Fore.WHITE)
        if self.usesTime():
            colored_record.asctime = self.formatTime(colored_record, self.datefmt)

        # Add color to the message
        colored_record.msg = f"{log_color}{colored_record.getMessage()}{Style.RESET_ALL}"
        colored_record.args = ()
        colored_record.levelname = f"{log_color}{colored_record.levelname}{Style.RESET_ALL}"
        colored_record.filename = f"{log_color}{colored_record.filename}{Style.RESET_ALL}"
        colored_record.name = f"{log_color}{colored_record.name}{Style.RESET_ALL}"

        # Use a custom field for formatted lineno
        formatted_lineno = f"{log_color}{colored_record.lineno}{Style.RESET_ALL}"

        # Format the log message
        formatted_message = super().format(colored_record)

        # Replace lineno placeholder in the final message
        return formatted_message.replace(f":{colored_record.lineno}", f":{formatted_lineno}")


def setup_logging(log_level: str = "INFO") -> None:
    assert log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], "Invalid log level"
    handler = logging.StreamHandler()

    handler.setFormatter(
        ColorFormatter("%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s")
    )
    root_level = getattr(logging, log_level)

    loggers = [
        "root",
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
        "openai",
        "urllib3",
        "httpcore",
        "aiokafka",
        "pymongo",
        "tzlocal",
        "apscheduler",
        "googleapiclient",
        "LiteLLM",
        "instructor",
        "httpx",
        "graphviz",
        "opentelemetry",
        "opensearch",
    ]
    for name in loggers:
        logger = logging.getLogger() if name == "root" else logging.getLogger(name)
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.propagate = False
        if name == "opentelemetry":
            logger.setLevel(logging.CRITICAL)
        elif name in {"uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", "root"}:
            logger.setLevel(root_level)
        else:
            logger.setLevel(logging.WARNING)
