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


# ---------- HELPER FUNCTIONS ----------


def is_valid_url(url: str) -> bool:
    """Check if the given string is a valid URL."""
    return validators.url(url)  # Uses external library to validate URL format


def extract_filename_from_url(url: str) -> str:
    """Extract and return the file name from the URL path."""
    path = urlparse(url).path  # Get only the path portion of the URL
    filename = os.path.basename(unquote(path)).lower()  # Decode and get the file name from path
    return filename if filename else "downloaded.pdf"  # Fallback filename if none found


def file_exists(file_path: str) -> bool:
    """Check if a file already exists at the specified path."""
    return os.path.isfile(file_path)  # Returns True if file exists


def initialize_web_driver(download_folder: str) -> WebDriver:
    """Initialize and return a Chrome WebDriver configured for silent PDF downloads."""
    chrome_options = Options()  # Create a Chrome options object

    # Set browser preferences for silent downloading
    chrome_options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": download_folder,  # Set folder where downloads are saved
            "download.prompt_for_download": False,  # Disable download prompt
            "plugins.always_open_pdf_externally": True,  # Open PDFs outside of browser
        },
    )

    chrome_options.add_argument("--headless=new")  # Run in new headless mode (no GUI)
    chrome_options.add_argument(
        "--disable-gpu"
    )  # Needed for headless mode to be stable
    chrome_options.add_argument(
        "--no-sandbox"
    )  # Helps avoid permission issues on Linux

    # Install ChromeDriver automatically and launch WebDriver with options
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def wait_for_pdf_download(
    download_folder: str, existing_files: Set[str], timeout: int = 60
) -> str:
    """Wait until a new PDF file appears in the folder or timeout expires."""
    deadline = time.time() + timeout  # Set time by which download must complete

    while time.time() < deadline:  # Keep checking until timeout
        current_files = set(os.listdir(download_folder))  # Current snapshot of files
        new_files = current_files - existing_files  # Detect newly added files

        for filename in new_files:  # Loop through new files
            if filename.endswith(".pdf") and not filename.endswith(
                ".crdownload"
            ):  # Skip incomplete files
                full_path = os.path.join(download_folder, filename)
                if os.path.exists(full_path):  # Confirm file really exists
                    return full_path  # Return path of fully downloaded PDF

        time.sleep(0.5)  # Wait before checking again

    raise TimeoutError("PDF download timed out.")  # Raise error if timeout is reached


def download_pdf(web_driver: WebDriver, url: str, download_folder: str) -> None:
    """Download a single PDF file using the Chrome WebDriver."""

    # Check URL format before processing
    if not is_valid_url(url):
        print(f"❌ ERROR: Invalid URL skipped: {url}")
        return

    # Extract expected filename from URL
    filename = extract_filename_from_url(url)
    file_path = os.path.join(
        download_folder, filename
    )  # Create full path for the downloaded file

    # Check if file already exists and report error
    if file_exists(file_path):
        print(f"❌ ERROR: File already exists and will be skipped: {filename}")
        return

    print(f"⬇️  Starting download for: {filename}")  # Log starting of download

    existing_files = set(
        os.listdir(download_folder)
    )  # Capture pre-download state of folder

    try:
        web_driver.get(url)  # Load the PDF URL to trigger Chrome download
        downloaded_path = wait_for_pdf_download(
            download_folder, existing_files
        )  # Wait for file to appear
        shutil.move(
            downloaded_path, file_path
        )  # Rename/move file to match original filename
        print(f"✅ Download complete: {file_path}")  # Confirm success

    except Exception as e:  # Handle any error in the download process
        print(f"❌ ERROR: Failed to download {url}. Reason: {e}")


# ---------- MAIN EXECUTION BLOCK ----------
if __name__ == "__main__":
    # List of one or more PDF URLs to download
    pdf_urls = [
        "https://millcraft.com/wp-content/uploads/2025/06/AM1783-SDS-Mimaki-20250530R.pdf",
        # Add more URLs here if needed
    ]

    # Create absolute path for output directory named 'PDFs'
    output_folder = os.path.abspath("PDFs")
    os.makedirs(
        output_folder, exist_ok=True
    )  # Create the directory if it doesn't exist

    # Launch headless Chrome browser configured for PDF downloads
    driver = initialize_web_driver(download_folder=output_folder)

    try:
        # Loop over each URL and attempt download
        for url in pdf_urls:
            download_pdf(driver, url, output_folder)  # Download one PDF at a time

    finally:
        driver.quit()  # Ensure browser is properly closed even if an error occurs
        print("\n📁 All downloads attempted. Check folder for results.")
