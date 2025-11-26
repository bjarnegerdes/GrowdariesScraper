import os
import time
import hashlib
import requests
from tqdm import tqdm  # falls du keine Progressbar willst, kannst du das weglassen

LINKS_FILE = "links.txt"
PROCESSED_FILE = "processed_links.txt"
OUTPUT_DIR = "pages"
DELAY_SECONDS = 1.0  # Pause zwischen Requests
MIN_SIZE_BYTES = 100 * 1024  # 100 KB Mindestgröße

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; GrowdiariesScraper/1.0; +https://example.com)"
}


def load_links(filename):
    """Liest alle Links aus einer Datei und gibt ein Set zurück."""
    if not os.path.exists(filename):
        return set()
    with open(filename, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def ensure_output_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def link_to_filename(link):
    """Erzeugt einen eindeutigen Dateinamen aus dem Link."""
    h = hashlib.md5(link.encode("utf-8")).hexdigest()
    return f"{h}.html"


def append_processed_link(link):
    """Hängt einen verarbeiteten Link an die processed_links-Datei an."""
    with open(PROCESSED_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")


def fetch_and_save(link):
    """
    Holt die Seite per HTTP, speichert das HTML im OUTPUT_DIR
    und gibt True zurück, wenn die Seite > 100 KB groß ist.
    """
    try:
        resp = requests.get(link, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"Fehler bei {link}: {e}")
        return False

    content_bytes = resp.content
    size_bytes = len(content_bytes)

    filename = link_to_filename(link)
    filepath = os.path.join(OUTPUT_DIR, filename)

    # HTML immer speichern (kannst du weglassen, wenn du kleine Seiten nicht brauchst)
    with open(filepath, "w", encoding="utf-8", errors="ignore") as f:
        f.write(resp.text)

    if size_bytes < MIN_SIZE_BYTES:
        print(f"Seite zu klein ({size_bytes} Bytes) -> NICHT als verarbeitet markieren: {link}")
        return False

    # Seite ist groß genug, wird als "erfolgreich" gewertet
    return True


def main():
    # Links laden und deduplizieren
    all_links = load_links(LINKS_FILE)
    print(f"Links in {LINKS_FILE}: {len(all_links)}")

    # Bereits verarbeitete Links laden
    processed_links = load_links(PROCESSED_FILE)
    print(f"Bereits verarbeitete Links in {PROCESSED_FILE}: {len(processed_links)}")

    # Nur neue Links verarbeiten
    to_process = sorted(all_links - processed_links)
    print(f"Zu verarbeitende Links: {len(to_process)}")

    if not to_process:
        print("Keine neuen Links zu verarbeiten. Fertig.")
        return

    ensure_output_dir(OUTPUT_DIR)

    # Loop über alle neuen Links mit Progressbar
    for link in tqdm(to_process, desc="Downloading pages"):
        success = fetch_and_save(link)
        if success:
            append_processed_link(link)
            processed_links.add(link)
        time.sleep(DELAY_SECONDS)

    print("Fertig! Gesamt verarbeitete Links:", len(processed_links))


if __name__ == "__main__":
    main()
