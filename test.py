import os
import time
import re
import hashlib
import requests
from itertools import cycle
from tqdm import tqdm

LINKS_FILE = "links.txt"
PROCESSED_FILE = "processed_links.txt"
OUTPUT_DIR = "api_pages"
DELAY_SECONDS = 60.0
MIN_SIZE_BYTES = 100 * 1024  # 100 KB Mindestgröße

# --------------------
# Deine rotierenden Configs
# --------------------
CONFIGS = {
    "cookie_string": "i18n_redirected=de; general_agree=true; _ga=GA1.1.473240708.1760281203; locale=de; ui:weeks-order=asc; auth:guest=9bxyppovtiptvhkvvoq4mj; auth:api=U2FsdGVkX1/qZrJuOTXqngnik+aZUurjT0zNFkmOFro3SV2Cai1bm5s+r930bJAR; ab_v_packages_banners=1308; ab_v_packages=82; ah_v_packages_banners=1269; ah_v_packages=173; ac_v_packages_banners=1630; ac_v_packages=173; _ga_K1T13ERM3V=GS2.1.s1764181545$o8$g1$t1764186497$j60$l0$h0",
    "headers": {
        "accept": "*/*",
        "accept-language": "de-DE,de;q=0.9,en-US;q=0.8,en-DE;q=0.7,en;q=0.6",
        "accept-encoding": "gzip, deflate, br, zstd",
        "authorization": "",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "priority": "u=1, i",
        "referer": "https://growdiaries.com/diaries/282089-grow-journal-by-mrdub",
        "sec-ch-ua": "\"Chromium\";v=\"142\", \"Google Chrome\";v=\"142\", \"Not_A Brand\";v=\"99\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "sec-fetch-site": "same-origin",
        "x-access": "U2FsdGVkX1/qZrJuOTXqngnik+aZUurjT0zNFkmOFro3SV2Cai1bm5s+r930bJAR",
        "x-guest": "9bxyppovtiptvhkvvoq4mj",
        "x-origin": "",
        "x-pass": "",
        "x-pass-old": "",
        "x-rniq": "i9brpnpqfbe",
        "x-uniq": "e03638e7d23ef4a783098159db731cf706189f07a8f71074bdca53c627211517",
        "x-uniq": "e03638e7d23ef4a783098159db731cf706189f07a8f71074bdca53c627211517"
    }
}

COOKIE_CONFIGS = {
    "i18n_redirected": "de",
    "general_agree": "true",
    "_ga": "GA1.1.473240708.1760281203",
    "locale": "de",
    "ui:weeks-order": "asc",
    "auth:guest": "9bxyppovtiptvhkvvoq4mj",
    "auth:api": "U2FsdGVkX1/qZrJuOTXqngnik+aZUurjT0zNFkmOFro3SV2Cai1bm5s+r930bJAR",
    "auth:api": "U2FsdGVkX1/qZrJuOTXqngnik+aZUurjT0zNFkmOFro3SV2Cai1bm5s+r930bJAR"
}
# --------------------
# Hilfsfunktionen
# --------------------

def load_links(filename):
    if not os.path.exists(filename):
        return set()
    with open(filename, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def ensure_output_dir(path):
    os.makedirs(path, exist_ok=True)


def extract_diary_id(link: str):
    """
    Holt die ID am Ende der Diary-URL.
    Beispiel: https://growdiaries.com/diaries/294456-grow-journal
              -> 294456
    """
    m = re.search(r"/diaries/(\d+)", link)
    if m:
        return m.group(1)
    return None


def id_to_filename(diary_id: str):
    # Du kannst auch einfach f"{diary_id}.json" machen; Hash nur falls du extra safe sein willst
    return f"{diary_id}.json"


def append_processed_link(link):
    with open(PROCESSED_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")


def build_cookie_dict_from_string(cookie_string: str):
    cookie_dict = {}
    for item in cookie_string.split("; "):
        if "=" in item:
            k, v = item.split("=", 1)
            cookie_dict[k] = v
    return cookie_dict


def fetch_diary_api(link, cfg, cookie_cfg):
    """
    Holt die Diary-Daten über die API und speichert sie.
    Nutzt rotierende Header/Cookies/Proxies wie in deinem Beispiel.
    """
    diary_id = extract_diary_id(link)
    if not diary_id:
        print(f"Konnte keine ID aus Link lesen, skip: {link}")
        return False

    api_url = f"https://growdiaries.com/api/v1/diaries/{diary_id}"

    browser_session = requests.Session()
    browser_session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
    })

    # Basis-Cookies aus cookie_config
    browser_session.cookies.update(cookie_cfg)

    # Cookies aus cookie_string
    cookie_dict = build_cookie_dict_from_string(cfg["cookie_string"])

    # Header vorbereiten
    headers = cfg["headers"].copy()
    # referer dynamisch auf den eigentlichen Diary-Link setzen
    headers["referer"] = link
    # falls ein "path" in den Headern steckt -> anpassen
    if "path" in headers:
        headers["path"] = f"/api/v1/diaries/{diary_id}"

    try:
        resp = browser_session.get(
            api_url,
            headers=headers,
            cookies=cookie_dict,
        )
        status = resp.status_code
    except Exception as e:
        print(f"Fehler bei Request ({link}): {e}")
        return False

    if status != 200:
        print(f"Status {status} für {api_url}, Link: {link}")
        return False

    content_bytes = resp.content
    size_bytes = len(content_bytes)

    filename = id_to_filename(diary_id)
    filepath = os.path.join(OUTPUT_DIR, filename)

    # JSON/Response speichern
    with open(filepath, "wb") as f:
        f.write(content_bytes)

    if size_bytes < MIN_SIZE_BYTES:
        print(f"Response zu klein ({size_bytes} Bytes) -> NICHT als verarbeitet markieren: {link}")
        return False

    return True


# --------------------
# Main
# --------------------

def main():
    ensure_output_dir(OUTPUT_DIR)

    all_links = load_links(LINKS_FILE)
    print(f"Links in {LINKS_FILE}: {len(all_links)}")

    processed_links = load_links(PROCESSED_FILE)
    print(f"Bereits verarbeitete Links: {len(processed_links)}")

    to_process = sorted(all_links - processed_links)
    print(f"Zu verarbeitende Links: {len(to_process)}")

    if not to_process:
        print("Keine neuen Links zu verarbeiten.")
        return

    for link in tqdm(to_process, desc="Fetching API diaries"):

        success = fetch_diary_api(link, CONFIGS, COOKIE_CONFIGS)
        if success:
            append_processed_link(link)
            processed_links.add(link)

        time.sleep(DELAY_SECONDS)

    print("Fertig! Gesamt verarbeitete Links:", len(processed_links))


if __name__ == "__main__":
    main()
