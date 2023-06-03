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
    _log_initiate_download_message(args)
    urls = _get_image_urls(args.tag)
    base_path = _get_save_base_path(args.tag)
    _initiate_download(urls, base_path, args)


def _parse_args() -> argparse.Namespace:
    """
    Parses command line arguments for download mode and thread count.

    Returns:
        argparse.Namespace: Parsed arguments as a Namespace object.
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
    """
    This function retrieves a dictionary mapping imgur IDs to
    lists of image URLs from Imgur's gallery tagged with a given tag.

    Args:
        tag (str): The tag to filter images by in Imgur's gallery.

    Returns:
        dict[str, list[str]]: A dictionary where each key is an
            imgur ID, and each value is a list of URLs associated with
            that imgur ID. Returns an empty dictionary if an error occurs
            while making the request or if no images are found for the
            provided tag.
    """
    headers = {"Authorization": f"Client-ID {CLIENT_ID}"}
    response = requests.get(f"https://api.imgur.com/3/gallery/t/{tag}", headers=headers)
    try:
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        logger.error(f"Error: {exc}")
        return {}

    try:
        items = response.json()["data"]["items"]
    except KeyError:
        logger.error(
            f"Error: No images were found. Check that the tag {tag} exists on Imgur."
        )
        return {}

    urls = {}
    for item in items:
        if "images" not in item:
            continue
        # Process e.g. "https://imgur.com/a/iTGAyBs" to "iTGAyBs" using pathlib
        imgur_id = Path(item["link"]).name
        # Multiple images can be associated with one imgur ID
        urls[imgur_id] = [image["link"] for image in item["images"]]
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
        urls: Dictionary with imgur IDs as keys and lists of URLs as values.
        base_path: Location to save downloaded images.
        args: Namespace with 'mode' and 'threads' for download settings.

    Returns:
        None
    """
    if args.mode == "threaded":
        _prepare_download_threaded(urls, base_path, args.threads)
    elif args.mode == "sequential":
        _prepare_download_sequential(urls, base_path)
    else:
        logger.error(f"Invalid mode: {args.mode}. Use 'threaded' or 'sequential'.")


def _prepare_download_sequential(urls: dict[str, list[str]], base_path: Path) -> None:
    """Downloads images from given urls and saves them at the specified path
    sequentially.

    A separate folder is created for each imgur ID that has multiple images.

    Args:
        urls (dict[str, list[str]]): A dictionary containing unique imgur IDs as keys
            and corresponding lists of image urls as values.
        base_path (Path): The path where the images should be saved.

    Returns:
        None
    """
    for imgur_id in urls:
        save_paths = _get_save_paths(imgur_id, urls[imgur_id], base_path)
        for url, save_path in zip(urls[imgur_id], save_paths):
            _download_single_image(url, save_path)


def _prepare_download_threaded(
    urls: dict[str, list[str]], base_path: Path, num_threads: int
) -> None:
    """
    This function initiates a multithreaded download of images. It uses a worker
    function `_download_images_worker` to download images concurrently. The function
    assigns URLs to threads and manages thread execution. Each thread downloads
    the images and saves them at the specified location. The function will
    block until all downloads are completed.


    Args:
        urls (dict[str, list[str]]): A dictionary where the key is the imgur id and
            the value is a list of URLs for the associated images.
        base_path (Path): The base directory path where the downloaded images will be saved.
        num_threads (int): The number of threads to use for the downloads.

    Returns:
        None
    """
    queue: Queue = Queue()
    threads = []
    for _ in range(num_threads):
        t = Thread(target=_download_images_worker, args=(queue,))
        t.start()
        threads.append(t)

    for imgur_id in urls:
        save_paths = _get_save_paths(imgur_id, urls[imgur_id], base_path)
        for url, save_path in zip(urls[imgur_id], save_paths):
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
        url, save_path = next_item
        _download_single_image(url, save_path)
        queue.task_done()


def _download_single_image(url: str, save_path: Path) -> None:
    """Downloads an image from a given url and saves it at the specified path.

    Args:
        url (str): The url from where the image needs to be downloaded.
        save_path (Path): The path where the downloaded image should be saved.

    Returns:
        None
    """
    response = requests.get(url)
    try:
        response.raise_for_status()
    except requests.exceptions.RequestException as http_error:
        logger.error(f"Error downloading url {url}:\n {http_error}")
        return
    with open(save_path, "wb") as file:
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


def _get_save_paths(imgur_id: str, urls: list[str], base_path: Path) -> list[Path]:
    """
    Generates a file path based on the given id and url.

    Args:
        imgur_id (str): The unique identifier for the image(s).
        urls list[str]: A list of urls of the image(s) to download.
        base_path (Path): The base directory to save the images in.

    Returns:
        list[Path]: A list of paths where the images should be saved.
    """
    save_paths = []
    if len(urls) > 1:
        (base_path / imgur_id).mkdir(parents=True, exist_ok=True)
    for url in urls:
        ext = Path(url).suffix[1:]
        if len(urls) > 1:
            save_paths.append(base_path / imgur_id / f"{imgur_id}.{ext}")
        else:
            save_paths.append(base_path / f"{imgur_id}.{ext}")
    return save_paths


if __name__ == "__main__":
    main()
