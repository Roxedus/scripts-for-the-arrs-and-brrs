#!/usr/bin/env python3

"""
Author: soup
Description: Script to automate hardlinking and cross-seeding for Usenet downloads.
"""

import os
import requests
import sys
from pathlib import Path
import argparse

# settings
base_path = "/home/user/Downloads/complete/"  # replace with the path where your completed Usenet downloads are stored
cross_base_url = "http://127.0.0.1:2468"  # replace with the base URL of your cross-seed instance
dest_path = "/home/user/torrents/qbittorrent/usenet/"  # replace with the path where you want to create hardlinks
unattended = False  # set to True to run without user interaction
recursive = True # set to False to run without traversing folders

if os.environ.get("SAB_COMPLETE_DIR", False):
    base_path = os.environ.get("SAB_COMPLETE_DIR")
    unattended = True
    POSTPROCESS_SUCCESS = 0
    POSTPROCESS_ERROR = 1

elif os.environ.get("NZBPP_DIRECTORY", False):
    base_path = os.environ.get("NZBPP_DIRECTORY")
    unattended = True
    POSTPROCESS_SUCCESS = 93
    POSTPROCESS_ERROR = 94

else:
    POSTPROCESS_SUCCESS = 0
    POSTPROCESS_ERROR = 1


def find_files(path: Path, extensions: tuple):
    for entry in path.iterdir():
        if entry.is_file() and entry.suffix in extensions:
            yield entry
        elif entry.is_dir() and recursive:
            yield from find_files(entry, extensions)


def hardlink_files(file_paths: list, dest: Path):
    for file_path in file_paths:
        dest_file = dest / file_path.name
        if not dest_file.exists():  # to prevent FileExistsError
            os.link(file_path, dest_file)
            yield dest_file


def send_webhook(url: str, directory_path: str):
    data = {"path": directory_path}
    response = requests.post(url + "/api/webhook", data=data)
    if response.status_code == 204:
        print("Trigger sent successfully.")
        sys.exit(POSTPROCESS_SUCCESS)
    else:
        print("Trigger failed.")
        sys.exit(POSTPROCESS_ERROR)


def user_prompt(question, default="no"):
    valid = {"yes": True, "y": True, "no": False, "n": False}
    prompt = " [Y/n] " if default == "yes" else " [y/N] "

    while True:
        print(question + prompt, end="")
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            print("Please respond with 'yes' or 'no' (or 'y' or 'n').")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process some files.")
    parser.add_argument(
        "--recursive", action="store", help="run script recursively in 'base_path'"
    )
    parser.add_argument(
        "--unattended", action="store", help="run script without user interaction"
    )
    args, unknown = parser.parse_known_args()

    unattended = unattended or args.unattended
    recursive = recursive or args.recursive

    files = list(find_files(Path(base_path), (".mkv", ".mp4")))
    print(f"{len(files)} non-hardlinked movies found.")

    if len(files) > 0:
        if unattended:
            print("Running in unattended mode.")
        else:
            if not user_prompt("Do you want to hardlink them?", default="no"):
                files = []

        hardlinked_files = list(hardlink_files(files, Path(dest_path)))

    if unattended or user_prompt(
        f"Do you want to trigger a cross-seed search in {dest_path}?", default="yes"
    ):
        print(f"Triggering cross-seed search in {dest_path}")
        send_webhook(cross_base_url, dest_path)
        sys.exit(POSTPROCESS_SUCCESS)
    else:
        print("Not triggering a cross-seed search")
        sys.exit(POSTPROCESS_SUCCESS)
