import os
from pathlib import Path

from datetime import datetime


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
    save_path = Path("images") / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    create_image_folder(save_path)
    return save_path
