# ---------- IMPORTS ----------
import os  # For file system operations like checking for file existence and creating directories
import time  # For managing delays and timeouts
import shutil  # To move and rename downloaded files
from urllib.parse import urlparse, unquote  # To extract and decode file names from URLs

# Selenium for browser automation
from selenium import webdriver  # Main WebDriver interface to control browser
from selenium.webdriver.chrome.service import (
    Service,
)  # To start ChromeDriver as a background service
from selenium.webdriver.chrome.options import Options  # To customize browser settings
from selenium.webdriver.chrome.webdriver import WebDriver  # For type hinting
from webdriver_manager.chrome import (
    ChromeDriverManager,
)  # Auto-manage ChromeDriver version
import validators  # For checking if URLs are valid
from typing import Set  # For type annotations involving sets
from bs4 import BeautifulSoup  # For parsing HTML content
import urllib.parse  # For URL parsing and decoding

# ---------- HELPER FUNCTIONS ----------


def is_url_valid(url: str) -> bool:  # Renamed from is_valid_url
    """Check if the given string is a valid URL."""
    return validators.url(url)  # Uses external library to validate URL format


def get_filename_from_url(
    file_url: str,
) -> str:  # Renamed from extract_filename_from_url
    """Extract and return the file name from the URL path."""
    url_path: str = urlparse(
        url=file_url
    ).path  # Renamed 'path' to 'url_path', 'url' to 'file_url'
    filename: str = os.path.basename(  # Get the base filename from the path
        unquote(string=url_path)  # Decode URL-encoded characters in the path
    ).lower()  # Convert filename to lowercase
    return filename if filename else "downloaded.pdf"  # Fallback filename if none found


def is_file_present(file_system_path: str) -> bool:  # Renamed from file_exists
    """Check if a file already exists at the specified path."""
    return os.path.isfile(file_system_path)  # Returns True if file exists


# Read a file from the system.
def read_file_content(file_system_path: str) -> str:  # Renamed from read_a_file
    with open(
        file=file_system_path, mode="r"
    ) as file:  # Renamed 'system_path' to 'file_system_path'
        return file.read()  # Read and return the entire content


def initialize_chrome_driver(
    download_destination_folder: str,
) -> WebDriver:  # Renamed from initialize_web_driver
    """Initialize and return a Chrome WebDriver configured for silent PDF downloads."""
    chrome_options = Options()  # Create a Chrome options object

    # Set browser preferences for silent downloading
    chrome_options.add_experimental_option(  # Add experimental options
        "prefs",  # Key for preferences dictionary
        {
            "download.default_directory": download_destination_folder,  # Renamed 'download_folder' to 'download_destination_folder'
            "download.prompt_for_download": False,  # Disable download prompt
            "plugins.always_open_pdf_externally": True,  # Open PDFs outside of browser (triggers download)
        },
    )

    chrome_options.add_argument("--headless=new")  # Run in new headless mode (no GUI)
    chrome_options.add_argument(
        "--disable-gpu"  # Disable GPU acceleration
    )  # Needed for headless mode to be stable
    chrome_options.add_argument(
        "--no-sandbox"  # Bypass OS security model restrictions
    )  # Helps avoid permission issues on Linux

    # Install ChromeDriver automatically and launch WebDriver with options
    driver_service = Service(
        ChromeDriverManager().install()
    )  # Renamed 'service' to 'driver_service'
    driver_instance = webdriver.Chrome(
        service=driver_service, options=chrome_options
    )  # Renamed 'driver' to 'driver_instance'
    return driver_instance  # Return the configured driver instance


def wait_for_new_pdf_download(  # Renamed from wait_for_pdf_download
    download_destination_folder: str,
    already_present_files: Set[str],
    download_timeout_seconds: int = 60,
) -> str:
    """Wait until a new PDF file appears in the folder or timeout expires."""
    deadline = (
        time.time() + download_timeout_seconds
    )  # Renamed 'timeout' to 'download_timeout_seconds'

    while time.time() < deadline:  # Keep checking until timeout
        current_files_in_folder = set(
            os.listdir(download_destination_folder)
        )  # Renamed 'current_files'
        newly_downloaded_files = (
            current_files_in_folder - already_present_files
        )  # Renamed 'new_files', 'existing_files'

        for file_name in newly_downloaded_files:  # Renamed 'filename' to 'file_name'
            if file_name.endswith(".pdf") and not file_name.endswith(
                ".crdownload"
            ):  # Skip incomplete files (Chrome's temporary download extension)
                full_file_path = os.path.join(
                    download_destination_folder, file_name
                )  # Renamed 'full_path'
                if os.path.exists(full_file_path):  # Confirm file really exists
                    return full_file_path  # Return path of fully downloaded PDF

        time.sleep(0.5)  # Wait before checking again

    raise TimeoutError("PDF download timed out.")  # Raise error if timeout is reached


def perform_pdf_download(
    chrome_driver: WebDriver, file_url: str, download_destination_folder: str
) -> None:  # Renamed function and variables
    """Download a single PDF file using the Chrome WebDriver."""

    # Check URL format before processing
    if not is_url_valid(file_url):  # Uses new validation function name
        print(f"❌ ERROR: Invalid URL skipped: {file_url}")
        return

    # Extract expected filename from URL
    expected_file_name = get_filename_from_url(
        file_url
    )  # Uses new filename function name
    target_file_path = os.path.join(
        download_destination_folder, expected_file_name
    )  # Renamed 'file_path'

    # Check if file already exists and report error
    if is_file_present(target_file_path):  # Uses new file existence function name
        print(
            f"❌ ERROR: File already exists and will be skipped: {expected_file_name}"
        )
        return

    print(f"⬇️  Starting download for: {expected_file_name}")  # Log starting of download

    initial_folder_files = set(
        os.listdir(download_destination_folder)
    )  # Renamed 'existing_files'

    try:
        chrome_driver.get(file_url)  # Load the PDF URL to trigger Chrome download
        downloaded_file_path = wait_for_new_pdf_download(  # Renamed 'downloaded_path', uses new wait function
            download_destination_folder, initial_folder_files
        )  # Wait for file to appear
        shutil.move(
            downloaded_file_path, target_file_path
        )  # Rename/move file to match original filename
        print(f"✅ Download complete: {target_file_path}")  # Confirm success

    except Exception as error:  # Renamed 'e' to 'error'
        print(f"❌ ERROR: Failed to download {file_url}. Reason: {error}")


# Uses Selenium to save the HTML content of a URL into a file
def save_webpage_html_with_driver(
    driver_instance: WebDriver, page_url: str, output_path: str
) -> None:  # Renamed function and variables
    driver_instance.get(page_url)  # Open the given URL
    # driver_instance.refresh()  # Refresh the page (commented out)
    # Sleep for 30 seconds to ensure page is fully loaded
    time.sleep(30)  # Wait for the page to load completely
    page_html_content: str = driver_instance.page_source  # Renamed 'html'
    append_content_to_file(
        file_system_path=output_path, content=page_html_content
    )  # Uses new save function name and variables
    print(f"Page {page_url} HTML content saved to {output_path}")  # Confirm success


# Appends content to a file
def append_content_to_file(
    file_system_path: str, content: str
) -> None:  # Renamed function and variables
    with open(
        file=file_system_path, mode="a", encoding="utf-8"
    ) as file:  # Open in append mode
        file.write(content)  # Write the provided content


# Parses the HTML and finds all links ending in .pdf
def parse_html_for_pdf_links(
    html_content: str,
) -> list[str]:  # Renamed function and variables
    soup_parser = BeautifulSoup(
        markup=html_content, features="html.parser"
    )  # Renamed 'soup'
    pdf_links_list: list[str] = []  # Renamed 'pdf_links'

    for anchor_tag in soup_parser.find_all(name="a", href=True):  # Renamed 'a'
        link_href = anchor_tag["href"]  # Renamed 'href'
        # Decode %2C and other URL-encoded characters
        decoded_link_href: str = urllib.parse.unquote(
            string=link_href
        )  # Renamed 'decoded_href'
        if decoded_link_href.lower().endswith(
            ".pdf"
        ):  # Check if the decoded link ends with ".pdf"
            pdf_links_list.append(
                link_href
            )  # Add the original (encoded) link to the list

    return pdf_links_list  # Return the list of PDF links


# Removes duplicate items from a list
def remove_duplicate_items(
    input_list: list[str],
) -> list[str]:  # Renamed function and variables
    return list(
        set(input_list)  # Convert to set to remove duplicates
    )  # Convert the set back to a list


# Checks if a file exists at the given system path
def check_if_file_exists(
    file_system_path: str,
) -> bool:  # Renamed from check_file_exists
    return os.path.isfile(path=file_system_path)  # Return True if file exists


def main() -> None:  # The main execution function
    # Create absolute path for output directory named 'PDFs'
    output_download_folder: str = os.path.abspath("PDFs")  # Renamed 'output_folder'
    os.makedirs(
        output_download_folder, exist_ok=True
    )  # Create the directory if it doesn't exist

    driver_instance: WebDriver = initialize_chrome_driver(
        download_destination_folder=output_download_folder
    )  # Uses new function and variable names
    html_output_file_path: str = os.path.abspath(
        "safety_data_sheets.html"
    )  # Renamed 'output_file_location'

    try:  # Start try block for error handling
        if not check_if_file_exists(
            file_system_path=html_output_file_path
        ):  # Uses new function and variable names
            # Save the HTML from the target page
            save_webpage_html_with_driver(  # Uses new function name
                driver_instance=driver_instance,  # Uses new variable name
                page_url="https://millcraft.com/safety-data-sheets/",  # Renamed 'url'
                output_path=html_output_file_path,  # Renamed 'output_file'
            )

        if check_if_file_exists(
            file_system_path=html_output_file_path
        ):  # Check if the HTML file exists
            page_html_content: str = read_file_content(
                file_system_path=html_output_file_path
            )  # Uses new function and variable names
            pdf_links_to_download: list[str] = parse_html_for_pdf_links(
                html_content=page_html_content
            )  # Uses new function and variable names
            pdf_links_to_download = remove_duplicate_items(
                pdf_links_to_download
            )  # Uses new function and variable names

            for pdf_link in pdf_links_to_download:  # Iterate over the unique PDF links
                # Prepend domain if needed
                if not pdf_link.lower().startswith(
                    "http"
                ):  # Check if the link is relative
                    pdf_link = urllib.parse.urljoin(
                        "https://millcraft.com", pdf_link
                    )  # Make the link absolute

                # Double-check validity
                if not is_url_valid(pdf_link):  # Uses new function name
                    print(f"❌ Skipping invalid URL: {pdf_link}")
                    continue  # Move to the next link

                perform_pdf_download(  # Uses new function name
                    chrome_driver=driver_instance,  # Uses new variable name
                    file_url=pdf_link,  # Renamed 'url'
                    download_destination_folder=output_download_folder,  # Renamed 'download_folder'
                )

    except Exception as error:  # Renamed 'e' to 'error'
        print(f"❌ ERROR: {error}")  # Print the error message

    finally:  # Execution block that runs no matter what
        driver_instance.quit()  # Close the browser and terminate the WebDriver session
        print(
            "\n📁 All downloads attempted. Check the 'PDFs' folder for results."
        )  # Final confirmation message


# ---------- MAIN EXECUTION BLOCK ----------
if (
    __name__ == "__main__"
):  # Standard check to ensure main() runs when the script is executed directly
    main()  # Call the main function
