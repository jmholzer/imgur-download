import argparse
import logging
import os
from pathlib import Path
from queue import Queue
from threading import Thread

import requests

from utils import create_image_folder, generate_save_path, timer

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
    save_path = generate_save_path(args.tag)
    _log_initiate_download_message(args)
    _initiate_download(urls, save_path, args)


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
        id = item["link"].rpartition("/")[2]
        urls[id] = [image["link"] for image in item["images"]]
    return urls


def _log_initiate_download_message(args: argparse.Namespace) -> None:
    """
    Logs a message to the console indicating the start of image download.

    Args:
        args: Namespace with values for 'tag', 'mode' and 'threads'.

    Returns:
        None
    """
    logger.info(f"Downloading images with tag '{args.tag}' in {args.mode} mode.")
    if args.mode == "threaded":
        logger.info(f"Using {args.threads} threads.")


def _initiate_download(
    urls: dict[str, list[str]], save_path: Path, args: argparse.Namespace
) -> None:
    """
    Starts image download in either 'threaded' or 'sequential' mode.

    Args:
        urls: Dictionary with image IDs as keys and lists of URLs as values.
        save_path: Location to save downloaded images.
        args: Namespace with 'mode' and 'threads' for download settings.

    Returns:
        None
    """
    if args.mode == "threaded":
        _download_images_threaded(urls, save_path, args.threads)
    elif args.mode == "sequential":
        _download_images_sequential(urls, save_path)
    else:
        logger.error(f"Invalid mode: {args.mode}. Use 'threaded' or 'sequential'.")


def _download_images_sequential(urls: dict[str, list[str]], save_path: Path) -> None:
    """Downloads images from given urls and saves them at the specified path
    sequentially.

    Each image is saved with its unique ID if multiple images belong to the same
    ID. A separate folder is created for each ID that has multiple images.

    Args:
        urls (dict[str, list[str]]): A dictionary containing unique IDs as keys
            and corresponding lists of image urls as values.
        save_path (Path): The path where the images should be saved.

    Returns:
        None
    """
    for id in urls:
        file_path = save_path
        if len(urls[id]) > 1:
            file_path = save_path / id
            create_image_folder(file_path)
        for index, url in enumerate(urls[id]):
            type = url.rpartition(".")[2]
            if len(urls[id]) > 1:
                _download_single_image(url, file_path / f"{index}.{type}")
            else:
                _download_single_image(url, file_path / f"{id}.{type}")


def _download_images_threaded(
    urls: dict[str, list[str]], save_path: Path, num_threads: int
) -> None:
    """Downloads images from given urls and saves them at the specified path
    using ten threads.

    Each image is saved with its unique ID if multiple images belong to the same
    ID. A separate folder is created for each ID that has multiple images.

    Args:
        urls (dict[str, list[str]]): A dictionary containing unique IDs as keys
            and corresponding lists of image urls as values.
        save_path (Path): The path where the images should be saved.

    Returns:
        None
    """
    queue = Queue()
    threads = []
    for _ in range(num_threads):
        t = Thread(target=_download_images_worker, args=(queue,))
        t.start()
        threads.append(t)

    for id in urls:
        file_path = save_path
        if len(urls[id]) > 1:
            file_path = save_path / id
            create_image_folder(file_path)
        for index, url in enumerate(urls[id]):
            type = url.rpartition(".")[2]
            if len(urls[id]) > 1:
                queue.put((url, file_path / f"{index}.{type}"))
            else:
                queue.put((url, file_path / f"{id}.{type}"))

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
        save_path (Path): The path where the downloaded image should be saved.

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


if __name__ == "__main__":
    main()
