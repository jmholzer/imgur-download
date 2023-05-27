# import json
import logging
import os

import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


TYPES = {"image/jpeg", "image/png"}
CLIENT_ID = os.environ["imgur_client_id"]


def _get_links() -> list[str]:
    """
    """
    headers = {"Authorization": f"Client-ID {CLIENT_ID}"}
    response = requests.get("https://api.imgur.com/3/gallery/hot/viral/0.json", headers=headers)
    try:
        response.raise_for_status()
    except requests.HTTPError as http_error:
        logger.error(f"Error: {http_error}")
        return []
    response_data = response.json()["data"]
    return [item['link'] for item in response_data]


if __name__ == "__main__":
    logger.warning(_get_links())
