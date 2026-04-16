"""Simple levelled logger writing to stdout/stderr."""
import sys
from typing import NoReturn

RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
PURPLE = "\033[95m"
RESET = "\033[0m"


class Logger:
    """Minimal logger with DEBUG/INFO/WARNING/ERROR levels."""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3

    def __init__(self) -> None:
        self._level = self.WARNING

    def set_level(self, level_str: str) -> None:
        level_str = level_str.strip().upper()
        if level_str == "DEBUG":
            self._level = self.DEBUG
        elif level_str == "INFO":
            self._level = self.INFO
        elif level_str == "WARNING":
            self._level = self.WARNING
        elif level_str == "ERROR":
            self._level = self.ERROR

    def debug(self, message: str) -> None:
        if self._level <= self.DEBUG:
            print(f"{PURPLE}[Debug]{RESET} {message}")

    def error(self, message: str) -> NoReturn:
        if self._level <= self.ERROR:
            sys.stderr.write(f"{RED}[Error] {message}{RESET}\n")
        sys.exit(1)

    def warning(self, message: str) -> None:
        if self._level <= self.WARNING:
            sys.stderr.write(f"{YELLOW}[Warning] {message}{RESET}\n")

    def info(self, message: str) -> None:
        if self._level <= self.INFO:
            print(f"{GREEN}[Info] {RESET}{message}")


logger = Logger()

if __name__ == "__main__":
    logger.info("This is an informational message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
