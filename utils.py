import logging
import os
from datetime import datetime
from pathlib import Path
from time import perf_counter

logger = logging.getLogger("main")


def create_image_folder(save_path: Path) -> None:
    """Creates a new folder at the specified path if it doesn't already exist.

    Args:
        save_path (Path): The path where the new folder should be created.

    Returns:
        None
    """
    os.makedirs(save_path, exist_ok=True)


def generate_save_path() -> None:
    """Generates a save path for images with a unique identifier based on the
    current timestamp.

    Returns:
        Path: The path object representing the newly created directory.
    """
    save_path = Path("images") / (
        "downloads_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    )
    create_image_folder(save_path)
    return save_path


def timer(func: callable) -> callable:
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
