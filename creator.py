import argparse
import json
import logging
import os

from recipe_scrapers import scrape_me

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def cleanup_json_files(directory, key=None, new_key=None, default_value=""):
    for file_path, content in find_json_files(directory, key):
        modified = False
        content_copy = dict(content)
        for k, value in content_copy.items():
            if value == "":
                del content[k]
                logging.info(f"Removed empty '{k}' from {file_path}")
                modified = True
        if new_key and new_key not in content:
            content[new_key] = default_value
            logging.info(
                f"Added '{new_key}' with default value '{default_value}' to {file_path}"
            )
            modified = True
        if modified:
            try:
                with open(file_path, "w", encoding="utf-8") as file:
                    json.dump(content, file, ensure_ascii=False, indent=2)
            except OSError as e:
                logging.error(f"Failed to write to {file_path}: {str(e)}")


def update_json_files(directory, key, attribute):
    """Update specified key in JSON files using local .testhtml files based on filenames."""
    for file_path, content in find_json_files(directory, key):
        if content is not None:
            html_path = file_path.replace(".json", ".testhtml")
            try:
                with open(html_path, encoding="utf-8") as f:
                    html_content = f.read()
                scraper = scrape_me("", html=html_content)  # Using local HTML content
                if hasattr(scraper, attribute):
                    new_value = getattr(scraper, attribute)()
                    if new_value and (key not in content or content[key] != new_value):
                        content[key] = new_value
                        logging.info(
                            f"Updated '{key}' in {file_path} to '{new_value}' from local HTML {html_path}"
                        )
                        with open(file_path, "w", encoding="utf-8") as file:
                            json.dump(content, file, ensure_ascii=False, indent=2)
            except Exception as e:
                logging.error(f"Error updating from HTML {html_path}: {str(e)}")


def find_json_files(directory, key=None):
    """Yield paths and content of JSON files that contain a specific key."""
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = json.load(f)
                        if content is not None and (key is None or key in content):
                            logging.info(f"'{key}' key found in file: {file_path}")
                            yield file_path, content
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to decode JSON from {file_path}: {str(e)}")
                except OSError as e:
                    logging.error(f"Failed to read {file_path}: {str(e)}")


def update_blank_keys_from_html(directory, key):
    """Update keys with empty string values using data from corresponding .testhtml files."""
    for file_path, content in find_json_files(directory, key):
        updated = False
        for k, v in list(content.items()):
            if v == "":
                html_path = file_path.replace(".json", ".testhtml")
                try:
                    with open(html_path, encoding="utf-8") as f:
                        html_content = f.read()
                    scraper = scrape_me(
                        "", html=html_content
                    )  # Initializing with empty URL since we use local HTML
                    new_value = getattr(scraper, key)()
                    if new_value:
                        content[k] = new_value
                        updated = True
                        logging.info(
                            f"Updated '{k}' in {file_path} to '{new_value}' from {html_path}"
                        )
                except Exception as e:
                    logging.error(f"Error updating from HTML {html_path}: {str(e)}")
        if updated:
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = json.load(f)
            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode JSON from {file_path}: {str(e)}")
                content = None  # Ensure content is set to None if an error occurs
        if content is not None:
            if key is None or key in content:
                logging.info(f"'{key}' key found in file: {file_path}")
                yield file_path, content
        else:
            logging.error(f"Content is None for file {file_path}")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Process JSON files for updates and cleanup."
    )
    parser.add_argument(
        "-d", "--directory", required=True, help="Directory to search for JSON files"
    )
    parser.add_argument(
        "-c",
        "--cleanup",
        action="store_true",
        help="Flag to clean up JSON files by removing empty keys",
    )
    parser.add_argument(
        "-n", "--new_key", help="New key to add if it does not exist in JSON files"
    )
    parser.add_argument(
        "-v", "--default_value", default="", help="Default value for the new key"
    )
    parser.add_argument(
        "-t",
        "--test",
        action="store_true",
        help="Flag to update content in JSON files based on canonical URLs",
    )
    parser.add_argument("-k", "--key", help="Key to update in JSON files")
    parser.add_argument(
        "-a",
        "--attribute",
        default="dietary_restrictions",
        help="Scraper attribute to use for updating the JSON key (default: 'keywords')",
    )
    parser.add_argument(
        "-u",
        "--update-blanks",
        default="update all blank keys in JSON files using corresponding .testhtml files",
        help="Scraper attribute to use for updating the JSON key (default: 'keywords')",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    if args.cleanup:
        logging.info(f"Running cleanup process for JSON files in {args.directory}...")
        cleanup_json_files(
            args.directory, new_key=args.new_key, default_value=args.default_value
        )
    elif args.test and args.key:
        logging.info(
            f"Running update process for JSON files to update '{args.key}' using '{args.attribute}' from web content..."
        )
        update_json_files(args.directory, args.key, args.attribute)
    elif args.update_blanks:
        logging.info(
            f"Running update process for blank keys in JSON files in {args.directory}..."
        )
        update_blank_keys_from_html(args.directory, args.key)
    else:
        logging.info(
            "Please specify an operation (-c, -t, or --update-blanks with -k)."
        )


if __name__ == "__main__":
    main()
