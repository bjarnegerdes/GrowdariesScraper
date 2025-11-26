import time
import math
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm

URL = "https://growdiaries.com/explore?tags=harvested,photoperiod,indoor,mass_harvests"
XPATH_COUNT = '//*[@id="app"]/div[7]/div/div[2]/div[1]/div[2]/div[1]/a[1]/span'
WAIT_BEFORE_SCROLL = 5
OUTPUT_FILE = "links.txt"


def setup_driver(headless=True):
    options = webdriver.ChromeOptions()

    # Headless mode
    if headless:
        options.add_argument("--headless=new")

    # Window & performance flags
    options.add_argument("--window-size=1920,1080")
    #options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-notifications")

    # Disable images & media (important for performance)
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.video": 2,
        "profile.managed_default_content_settings.autoplay": 2,
        "profile.default_content_setting_values.media_stream": 2,
    }
    options.add_experimental_option("prefs", prefs)

    # Additional hard-disable for images
    options.add_argument("--blink-settings=imagesEnabled=false")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver


def get_total_pages(driver):
    elem = driver.find_element(By.XPATH, XPATH_COUNT)
    num = elem.text.strip().replace(".", "").replace(",", "")
    total_items = int(num)
    pages = math.ceil(total_items / 20)
    print(f"Gefunden: {total_items} Items -> {pages} Scrolls")
    return pages


def extract_diary_links(driver):
    """Extrahiert nur Links wie https://growdiaries.com/diaries/..."""
    anchors = driver.find_elements(By.TAG_NAME, "a")
    links = set()

    for a in anchors:
        href = a.get_attribute("href")
        if href and href.startswith("https://growdiaries.com/diaries/"):
            links.add(href)

    return links


def load_existing_links():
    """Lädt existierende Links einmalig in ein Set."""
    if not os.path.exists(OUTPUT_FILE):
        return set()

    with open(OUTPUT_FILE, "r") as f:
        return set(line.strip() for line in f.readlines())


def append_links(new_links):
    """Hängt neue Links an die Datei an (kein Lesen mehr)."""
    if not new_links:
        return

    with open(OUTPUT_FILE, "a") as f:
        for link in sorted(new_links):
            f.write(link + "\n")


def main():
    driver = setup_driver(headless=False)

    try:
        print(f"Öffne Seite: {URL}")
        driver.get(URL)
        time.sleep(5)

        pages = get_total_pages(driver)

        # Existierende Links nur einmal laden
        existing_links = load_existing_links()
        print(f"Bereits vorhandene Links: {len(existing_links)}")

        # Erste Runde Extraktion
        current_links = extract_diary_links(driver)
        new_links = current_links - existing_links
        append_links(new_links)
        existing_links |= new_links
        if new_links:
            print(f"+{len(new_links)} neue Links (gesamt: {len(existing_links)})")

        # Scroll-Loop mit tqdm
        for i in tqdm(range(pages), desc="Scrolling"):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(WAIT_BEFORE_SCROLL)

        print("\nScraping abgeschlossen!")
        print(f"Finale Anzahl Links: {len(existing_links)}")

    finally:
        current_links = extract_diary_links(driver)
        new_links = current_links - existing_links
        append_links(new_links)
        existing_links |= new_links
        driver.quit()


if __name__ == "__main__":
    main()
