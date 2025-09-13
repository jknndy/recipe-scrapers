import argparse
import json
import os
import pathlib

import requests
from reorder_json_keys import reorder_json_keys

from recipe_scrapers import SCRAPERS, scrape_html
from recipe_scrapers._abstract import HEADERS
from recipe_scrapers._exceptions import (
    ElementNotFoundInHtml,
    SchemaOrgException,
    StaticValueException,
    WebsiteNotImplementedError,
    OpenGraphException,
)


def safe_call(scraper, method_name, default=None):
    try:
        return getattr(scraper, method_name)()
    except (
        AttributeError,
        NotImplementedError,
        SchemaOrgException,
        ElementNotFoundInHtml,
        StaticValueException,
        WebsiteNotImplementedError,
        TypeError,
        OpenGraphException,
    ):
        return default


def convert_to_serializable(obj):
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    else:
        return obj


def update_testcase(json_file: pathlib.Path) -> None:
    """Update testcase by downloading the latest version of the html
    and run the scraper on it to create a new version of the json file.
    Assumes the json file is in the standard file tree.

    Args:
        json_file (pathlib.Path): The original json file.

    """
    json_file = json_file.absolute()
    html_file = json_file.with_suffix(".testhtml")
    orig_data = json.loads(json_file.read_text(encoding="utf-8"))

    original_source_uri = orig_data.get("source_uri")

    url = orig_data.get("source_uri") or orig_data.get("canonical_url")
    if not url:
        raise ValueError(f"No source_uri or canonical_url found in {json_file}")

    site_class = html_file.parent.name
    org_url = f"http://{site_class}"

    if not html_file.exists():
        raise FileNotFoundError(f"HTML file not found: {html_file}")

    html_data = requests.get(url, headers=HEADERS, timeout=10).content.decode("utf-8")
    html_file.write_text(html_data, encoding="utf-8")
    supported_only = site_class in SCRAPERS
    actual = scrape_html(
        html=html_data,
        org_url=org_url,
        online=False,
        supported_only=supported_only,
    )

    new_data = actual.to_json()

    if "instructions" in new_data:
        del new_data["instructions"]

    ingredient_groups = safe_call(actual, "ingredient_groups", "")
    if ingredient_groups and len(ingredient_groups) > 1:
        new_data["ingredient_groups"] = convert_to_serializable(ingredient_groups)
    elif "ingredient_groups" in new_data:
        del new_data["ingredient_groups"]

    new_data = {
        k: v
        for k, v in new_data.items()
        if v is not None and v != "" and v != [] and v != {}
    }

    if original_source_uri is not None:
        new_data["source_uri"] = original_source_uri

    json_file.write_text(
        json.dumps(new_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    reorder_json_keys(str(json_file), quiet=True)


def process_folder(folder_path: pathlib.Path) -> None:
    """Process all JSON files in a folder and its subfolders."""
    json_files = []

    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".json"):
                json_path = pathlib.Path(root) / file
                json_files.append(json_path)

    print(f"Found {len(json_files)} JSON files to process")

    for i, json_file in enumerate(json_files, 1):
        print(f"Processing {i}/{len(json_files)}: {json_file}")
        try:
            update_testcase(json_file)
        except Exception as e:
            print(f"Error processing {json_file}: {type(e).__name__}: {e}")
            continue


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch the latest version of a recipe and update the test data",
    )
    parser.add_argument(
        "path", help="The JSON file or folder containing JSON files to process"
    )

    args = parser.parse_args()
    path = pathlib.Path(args.path)

    if path.is_file():
        update_testcase(path)
    elif path.is_dir():
        process_folder(path)
    else:
        print(f"Error: {path} is neither a file nor a directory")
