import logging
import os

import requests

from utils import create_image_folder, generate_save_path

from pathlib import Path

from queue import Queue
from threading import Thread

TYPES = {"image/jpeg", "image/png"}
CLIENT_ID = os.environ["imgur_client_id"]


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """
    The main function of the script.

    Fetches a dictionary of image URLs by calling the _get_image_urls() function,
    then downloads the images and saves them in the "images" directory.

    Returns:
        None
    """
    urls = _get_image_urls()
    save_path = generate_save_path()
    _download_images_threaded(urls, save_path)


def _get_image_urls() -> dict[str, list[str]]:
    """Fetches and returns links to viral images from Imgur's hot gallery.

    This function sends a GET request to Imgur's hot/viral gallery endpoint
    using a client ID for authorization. It returns a list of links from the
    response data. If an HTTP error occurs during the request, it logs the
    error and returns an empty list.

    Returns:
        list[str]: List of image URLs. If an error occurs, returns an empty list.
    """
    headers = {"Authorization": f"Client-ID {CLIENT_ID}"}
    response = requests.get(
        "https://api.imgur.com/3/gallery/t/astronomy", headers=headers
    )
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


def _download_images_threaded(urls: dict[str, list[str]], save_path: Path) -> None:
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
    for _ in range(10):
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
