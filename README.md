# Imgur Image Downloader

This project is a Python script that enables you to download tagged images from [Imgur](https://imgur.com/).

## Download Modes

This script supports two download modes: `sequential` and `threaded`.

- `Sequential`: In this mode, images are downloaded one after another using only the main thread of the process.

- `Threaded`: This mode creates multiple threads to download images concurrently.

The script measures and logs the time taken to download the images in both modes. This enables you to see the effect of using the different modes and different numbers of threads on the script's performance.

## Requirements

The project's only dependency is the `requests` module, which can be installed using pip:

```bash
pip install requests
```

The script also requires an Imgur client ID which should be set in your environment variables as `imgur_client_id`. To obtain an Imgur client ID, [create an account on Imgur](https://help.imgur.com/hc/en-us/articles/210076633-Create-an-Account) and follow the [instructions on registering an application](https://api.imgur.com/oauth2/addclient).

## How to Run

To run the script, you need to use the command line. Navigate to the directory containing the script, then run the command with the following format:

```bash
python download.py --tag <tag> --mode <mode> [--threads <threads>]
```

Where:

- `<script name>` is the name of the python file.
- `<tag>` is the tag of the images you want to download. For example, `astronomy` or `cats`.
- `<mode>` is the download mode which can be either `threaded` or `sequential`.
- `<threads>` (optional) is the number of threads to use in `threaded` mode. Default is `10`. Only valid when `--mode=threaded`.

An example command to download images tagged with `astronomy` using 10 threads is:

```bash
python download.py --tag astronomy --mode threaded --threads 12
```

## Imgur Tags

Examples of Imgur tags you can use include: `astronomy`, `cats`, `cars`, `nature`, `earth`.

## Notes

The downloaded images will be saved in an `images` directory in the same location as the script. Each run will save its images in a new directory with the current time stamp. For tags with multiple images, each image will be saved in a separate directory within this top-level directory.
