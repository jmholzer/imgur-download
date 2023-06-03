import logging
from time import perf_counter
from typing import Callable

logger = logging.getLogger("main")


def timer(func: Callable) -> Callable:
    """Decorator that prints the execution time of a function.

    Args:
        func (function): The function to be decorated.

    Returns:
        function: The decorated function.
    """

    def wrapper(*args, **kwargs):
        start_time = perf_counter()
        result = func(*args, **kwargs)
        end_time = perf_counter()
        logger.info("Execution time: %.1f seconds", end_time - start_time)
        return result

    return wrapper
