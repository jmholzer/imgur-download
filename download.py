import argparse
import logging
import os
from datetime import datetime
from pathlib import Path
from queue import Queue
from threading import Thread

import requests

from utils import timer

TYPES = {"image/jpeg", "image/png"}
CLIENT_ID = os.environ["imgur_client_id"]


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")


@timer
def main() -> None:
    """
    The main function of the script.

    Fetches a dictionary of image URLs by calling the _get_image_urls() function,
    then downloads the images and saves them in the "images" directory.

    Returns:
        None
    """
    args = _parse_args()
    urls = _get_image_urls(args.tag)
    base_path = _get_save_base_path(args.tag)
    _log_initiate_download_message(args)
    _initiate_download(urls, base_path, args)


def _parse_args() -> argparse.Namespace:
    """
    Parses command line arguments for download mode and thread count.

    Returns:
        Parsed arguments as a Namespace object.
    """
    parser = argparse.ArgumentParser(
        description="Download images from Imgur's gallery of a tag."
    )
    parser.add_argument(
        "--tag",
        type=str,
        required=True,
        help=(
            "Choose a tag to download images from. For example, 'astronomy' or"
            " 'cats'."
        ),
    )
    parser.add_argument(
        "--mode",
        type=str,
        required=True,
        choices=["threaded", "sequential"],
        help=(
            "Choose either 'threaded' for downloading images using multiple"
            " threads or 'sequential' for sequential downloading."
        ),
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=10,
        help=(
            "Number of threads to use in 'threaded' mode. Default is 10. Only"
            " valid when --mode=threaded."
        ),
    )
    return parser.parse_args()


def _get_image_urls(tag: str) -> dict[str, list[str]]:
    """Fetches and returns links to viral images from Imgur's hot gallery.

    This function sends a GET request to Imgur's hot/viral gallery endpoint
    using a client ID for authorization. It returns a list of links from the
    response data. If an HTTP error occurs during the request, it logs the
    error and returns an empty list.

    Args:
        tag (str): The tag to search for.

    Returns:
        dict[str, list[str]]: List of image URLs. If an error occurs, returns an empty list.
    """
    headers = {"Authorization": f"Client-ID {CLIENT_ID}"}
    response = requests.get(f"https://api.imgur.com/3/gallery/t/{tag}", headers=headers)
    try:
        response.raise_for_status()
    except requests.HTTPError as http_error:
        logger.error(f"Error: {http_error}")
        return {}
    urls = {}
    for item in response.json()["data"]["items"]:
        if "images" not in item:
            continue
        image_id = item["link"].rpartition("/")[2]
        urls[image_id] = [image["link"] for image in item["images"]]
    return urls


def _log_initiate_download_message(args: argparse.Namespace) -> None:
    """
    Logs a message to the console indicating the start of image download.

    Args:
        args: Namespace with values for 'tag', 'mode' and 'threads'.

    Returns:
        None
    """
    message = f"Downloading images with tag '{args.tag}' in {args.mode} mode."
    if args.mode == "threaded":
        message += f" Using {args.threads} threads."
    logger.info(message)


def _initiate_download(
    urls: dict[str, list[str]], base_path: Path, args: argparse.Namespace
) -> None:
    """
    Starts image download in either 'threaded' or 'sequential' mode.

    Args:
        urls: Dictionary with image IDs as keys and lists of URLs as values.
        base_path: Location to save downloaded images.
        args: Namespace with 'mode' and 'threads' for download settings.

    Returns:
        None
    """
    if args.mode == "threaded":
        _download_images_threaded(urls, base_path, args.threads)
    elif args.mode == "sequential":
        _download_images_sequential(urls, base_path)
    else:
        logger.error(f"Invalid mode: {args.mode}. Use 'threaded' or 'sequential'.")


def _download_images_sequential(urls: dict[str, list[str]], base_path: Path) -> None:
    """Downloads images from given urls and saves them at the specified path
    sequentially.

    Each image is saved with its unique ID if multiple images belong to the same
    ID. A separate folder is created for each ID that has multiple images.

    Args:
        urls (dict[str, list[str]]): A dictionary containing unique IDs as keys
            and corresponding lists of image urls as values.
        base_path (Path): The path where the images should be saved.

    Returns:
        None
    """
    for image_id in urls:
        save_paths = _get_save_paths(image_id, urls[image_id], base_path)
        for url, save_path in zip(urls[image_id], save_paths):
            _download_single_image(url, save_path)


def _download_images_threaded(
    urls: dict[str, list[str]], base_path: Path, num_threads: int
) -> None:
    """Downloads images from given urls and saves them at the specified path
    using ten threads.

    Each image is saved with its unique ID if multiple images belong to the same
    ID. A separate folder is created for each ID that has multiple images.

    Args:
        urls (dict[str, list[str]]): A dictionary containing unique IDs as keys
            and corresponding lists of image urls as values.
        base_path (Path): The path where the images should be saved.

    Returns:
        None
    """
    queue = Queue()
    threads = []
    for _ in range(num_threads):
        t = Thread(target=_download_images_worker, args=(queue,))
        t.start()
        threads.append(t)

    for image_id in urls:
        save_paths = _get_save_paths(image_id, urls[image_id], base_path)
        for url, save_path in zip(urls[image_id], save_paths):
            queue.put((url, save_path))

    # add sentinels for each thread
    for _ in threads:
        queue.put(None)

    queue.join()

    for t in threads:
        t.join()


def _download_images_worker(queue: Queue) -> None:
    """Worker function for a thread that downloads urls stored in a Queue.

    Args:
        queue (Queue): A queue object that contains the image urls.

    Returns:
        None
    """
    while True:
        next_item = queue.get()
        if next_item is None:
            queue.task_done()
            break
        url, file_path = next_item
        _download_single_image(url, file_path)
        queue.task_done()


def _download_single_image(url: str, file_path: Path) -> None:
    """Downloads an image from a given url and saves it at the specified path.

    Args:
        url (str): The url from where the image needs to be downloaded.
        base_path (Path): The path where the downloaded image should be saved.

    Returns:
        None
    """
    response = requests.get(url)
    try:
        response.raise_for_status()
    except requests.HTTPError as http_error:
        logger.error(f"Error downloading url {url}:\n {http_error}")
        return False
    with open(file_path, "wb") as file:
        file.write(response.content)
    logger.info(f"Successfully downloaded {url}")


def _get_save_base_path(tag: str) -> Path:
    """Generates a save path for images with a unique identifier based on the
    current timestamp.

    Args:
        tag (str): The tag to be used for the image search.

    Returns:
        Path: The path object representing the newly created directory.
    """
    save_path = Path("images") / (
        f"{tag}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    )
    save_path.mkdir(parents=True, exist_ok=True)
    return save_path


def _get_save_paths(image_id: str, urls: list[str], base_path: Path) -> list[Path]:
    """
    Generates a file path based on the given id and url.

    Args:
        image_id (str): The unique identifier for the image(s).
        url list[str]: A list of urls of the image(s) to download.
        base_path (Path): The base directory to save the images in.

    Returns:
        list[Path]: A list of paths where the images should be saved.
    """
    save_paths = []
    if len(urls) > 1:
        (base_path / image_id).mkdir(parents=True, exist_ok=True)
    for url in urls:
        ext = url.rpartition(".")[2]
        if len(urls) > 1:
            save_paths.append(base_path / image_id / f"{image_id}.{ext}")
        else:
            save_paths.append(base_path / f"{image_id}.{ext}")
    return save_paths


if __name__ == "__main__":
    main()
