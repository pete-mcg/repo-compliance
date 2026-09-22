"""Small timing helper for synchronous functions."""

import logging
from collections.abc import Callable
from functools import wraps
from time import perf_counter


def timed[**Parameters, ReturnType](
    function: Callable[Parameters, ReturnType],
) -> Callable[Parameters, ReturnType]:
    """Log elapsed time at DEBUG, preserving the return value and exceptions."""
    logger = logging.getLogger(function.__module__)

    @wraps(function)
    def wrapper(*args: Parameters.args, **kwargs: Parameters.kwargs) -> ReturnType:
        started = perf_counter()
        try:
            return function(*args, **kwargs)
        finally:
            logger.debug("%s took %.2fs", function.__name__, perf_counter() - started)

    return wrapper
