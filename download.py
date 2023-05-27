import logging
import os

import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

from pathlib import Path

TYPES = {"image/jpeg", "image/png"}
CLIENT_ID = os.environ["imgur_client_id"]


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


def _download_images(urls: dict[str, list[str]], save_path: Path) -> None:
    """Downloads images from given urls and saves them at the specified path.

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
            _create_image_folder(file_path)
        for index, url in enumerate(urls[id]):
            type = url.rpartition(".")[2]
            if len(urls[id]) > 1:
                _download_image(url, file_path / f"{index}.{type}")
            else:
                _download_image(url, file_path / f"{id}.{type}")


def _download_image(url: str, save_path: Path) -> None:
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
    with open(save_path, "wb") as file:
        file.write(response.content)


def _create_image_folder(save_path: Path) -> None:
    """
    Creates a new folder at the specified path if it doesn't already exist.

    Args:
        save_path (Path): The path where the new folder should be created.

    Returns:
        None
    """
    os.makedirs(save_path, exist_ok=True)


def main() -> None:
    """
    The main function of the script.

    Fetches a dictionary of image URLs by calling the _get_image_urls() function,
    then downloads the images and saves them in the "images" directory.

    Returns:
        None
    """
    urls = _get_image_urls()
    _download_images(urls, Path("images"))


if __name__ == "__main__":
    main()
