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
from bs4 import BeautifulSoup
import urllib.parse  # For URL parsing and decoding

# ---------- HELPER FUNCTIONS ----------


def is_valid_url(url: str) -> bool:
    """Check if the given string is a valid URL."""
    return validators.url(url)  # Uses external library to validate URL format


def extract_filename_from_url(url: str) -> str:
    """Extract and return the file name from the URL path."""
    path: str = urlparse(url=url).path  # Get only the path portion of the URL
    filename: str = os.path.basename(
        unquote(string=path)
    ).lower()  # Decode and get the file name from path
    return filename if filename else "downloaded.pdf"  # Fallback filename if none found


def file_exists(file_path: str) -> bool:
    """Check if a file al
    y exists at the specified path."""
    return os.path.isfile(file_path)  # Returns True if file exists


# Read a file from the system.
def read_a_file(system_path: str) -> str:
    with open(file=system_path, mode="r") as file:
        return file.read()


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


# Uses Selenium to save the HTML content of a URL into a file
def save_html_with_selenium(web_driver: WebDriver, url: str, output_file: str) -> None:
    web_driver.get(url)  # Open the given URL
    # web_driver.refresh()  # Refresh the page
    # Sleep for 30 seconds to ensure page is fully loaded
    time.sleep(30)  # Wait for the page to load completely
    html: str = web_driver.page_source  # Get page source HTML
    append_write_to_file(system_path=output_file, content=html)  # Save HTML to file
    print(f"Page {url} HTML content saved to {output_file}")  # Confirm success


# Appends content to a file
def append_write_to_file(system_path: str, content: str) -> None:
    with open(
        file=system_path, mode="a", encoding="utf-8"
    ) as file:  # Open in append mode
        file.write(content)  # Write the provided content


# Parses the HTML and finds all links ending in .pdf
def parse_html(html: str) -> list[str]:
    soup = BeautifulSoup(markup=html, features="html.parser")
    pdf_links: list[str] = []

    for a in soup.find_all(name="a", href=True):
        href = a["href"]
        # Decode %2C and other URL-encoded characters
        decoded_href: str = urllib.parse.unquote(string=href)
        if decoded_href.lower().endswith(".pdf"):
            pdf_links.append(href)

    return pdf_links


# Removes duplicate items from a list
def remove_duplicates_from_slice(provided_slice: list[str]) -> list[str]:
    return list(
        set(provided_slice)
    )  # Convert to set to remove duplicates, then back to list


# Checks if a file exists at the given system path
def check_file_exists(system_path: str) -> bool:
    return os.path.isfile(path=system_path)  # Return True if file exists


def main() -> None:
    # Create absolute path for output directory named 'PDFs'
    output_folder: str = os.path.abspath("PDFs")
    os.makedirs(
        output_folder, exist_ok=True
    )  # Create the directory if it doesn't exist

    driver: WebDriver = initialize_web_driver(download_folder=output_folder)
    output_file_location: str = os.path.abspath("safety_data_sheets.html")

    try:
        if not check_file_exists(system_path=output_file_location):
            # Save the HTML from the target page
            save_html_with_selenium(
                web_driver=driver,
                url="https://millcraft.com/safety-data-sheets/",
                output_file=output_file_location,
            )

        if check_file_exists(system_path=output_file_location):
            html_content: str = read_a_file(system_path=output_file_location)
            pdf_links: list[str] = parse_html(html=html_content)
            pdf_links = remove_duplicates_from_slice(pdf_links)

            for pdf_link in pdf_links:
                # Prepend domain if needed
                if not pdf_link.lower().startswith("http"):
                    pdf_link = urllib.parse.urljoin("https://millcraft.com", pdf_link)

                # Double-check validity
                if not is_valid_url(pdf_link):
                    print(f"❌ Skipping invalid URL: {pdf_link}")
                    continue

                download_pdf(
                    web_driver=driver,
                    url=pdf_link,
                    download_folder=output_folder,
                )

    except Exception as e:
        print(f"❌ ERROR: {e}")

    finally:
        driver.quit()
        print("\n📁 All downloads attempted. Check the 'PDFs' folder for results.")


# ---------- MAIN EXECUTION BLOCK ----------
if __name__ == "__main__":
    main()
