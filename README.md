# Imgur Image Downloader

This project is a Python script that enables you to download images from Imgur galleries based on a given tag. It leverages Python's multi-threading capabilities to speed up the download process. This script requires Python 3.9 or later.

## Download Modes

This script supports two download modes: `sequential` and `threaded`.

- `Sequential`: In this mode, images are downloaded one after another. This is a slower method but has the advantage of being straightforward and easy to debug if anything goes wrong.

- `Threaded`: This mode uses Python's multi-threading capabilities. Multiple images are downloaded concurrently which results in faster downloads. The number of threads can be adjusted depending on your system capabilities and network conditions.

The script measures and logs the time taken to download the images in both modes. This can help you evaluate the efficiency of the threaded mode and adjust the number of threads for optimal performance.

## Requirements

The Python dependencies can be installed using pip:

```bash
pip install requests
```

The project also needs an Imgur client ID which should be set in your environment variables as `imgur_client_id`. To obtain an Imgur client ID, follow the instructions on [Imgur's API documentation](https://apidocs.imgur.com/).

## How to Run

To run the script, you need to use the command line. Navigate to the directory containing the script, then run the command with the following format:

```bash
python <script name> --tag <tag> --mode <mode> [--threads <threads>]
```

Where:

- `<script name>` is the name of the python file.
- `<tag>` is the tag of the images you want to download. For example, `astronomy` or `cats`.
- `<mode>` is the download mode which can be either `threaded` or `sequential`. 
- `<threads>` (optional) is the number of threads to use in `threaded` mode. Default is `10`. Only valid when `--mode=threaded`.

An example command to download images tagged with `astronomy` using 10 threads is:

```bash
python imgur_downloader.py --tag astronomy --mode threaded --threads 10
```

## Imgur Tags

Here are some examples of Imgur tags you can use:

- astronomy
- cats
- dogs
- cars
- nature
- art
- science
- history
- space
- earth

Remember to check that the tag exists on Imgur.

## Notes

The downloaded images will be saved in an `images` directory in the same location as the script. Each tag will have its own directory, with a unique identifier based on the current timestamp. For tags with multiple images, each image will be saved in a separate directory.
