import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright

BASE_URL = "https://game3rb.com/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}

def fetch_all_games():
    all_urls = []
    page = 1
    while True:
        url = f"{BASE_URL}page/{page}/" if page > 1 else BASE_URL
        resp = requests.get(url, timeout=30, headers=HEADERS)
        if resp.status_code != 200:
            break
        soup = BeautifulSoup(resp.text, "html.parser")
        links = soup.select("div#entry-pic a")
        if not links:
            break
        all_urls.extend([a["href"] for a in links])
        print(f"  Page {page}: {len(links)} jeux")
        page += 1
        time.sleep(2)
    return all_urls

def scrape_game(browser, url):
    page = browser.new_page()
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2000)

    # Titre
    title_el = page.query_selector("meta[property='og:title']")
    title_text = title_el.get_attribute("content") if title_el else page.title()

    # Magnet
    magnet_href = None
    magnet_el = page.query_selector("a[href^='magnet:']")
    if magnet_el:
        magnet_href = magnet_el.get_attribute("href")
    else:
        input_el = page.query_selector("input[value^='magnet:']")
        if input_el:
            magnet_href = input_el.get_attribute("value")
        else:
            body = page.inner_text("body")
            m = re.search(r'magnet:\?xt=urn:btih:[a-f0-9]+[^"\'<>\s]*', body)
            if m:
                magnet_href = m.group(0)

    # Taille
    size_text = "Unknown"
    size_el = page.query_selector(".file-size, .size, [class*='size']")
    if size_el:
        size_text = size_el.inner_text().strip()

    # Date
    date_el = page.query_selector("time, .date, [class*='date']")
    date_text = date_el.inner_text().strip() if date_el else datetime.utcnow().strftime("%Y-%m-%d")

    page.close()

    if not magnet_href:
        return None

    return {
        "title": title_text.strip(),
        "fileSize": size_text,
        "uris": [magnet_href],
        "uploadDate": date_text
    }

def main():
    # Scraping incrémental
    try:
        with open("source.json", "r") as f:
            old = json.load(f)
        old_urls = {d["uris"][0] for d in old["downloads"]}
    except (FileNotFoundError, json.JSONDecodeError):
        old = None
        old_urls = set()

    urls = fetch_all_games()
    new_urls = [u for u in urls if u not in old_urls]
    print(f"Found {len(urls)} games, {len(new_urls)} new")

    new_downloads = []
    if new_urls:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            with ThreadPoolExecutor(max_workers=3) as pool:
                futures = {pool.submit(scrape_game, browser, u): u for u in new_urls}
                for i, fut in enumerate(as_completed(futures)):
                    try:
                        d = fut.result()
                        if d:
                            new_downloads.append(d)
                        print(f"  [{i+1}/{len(new_urls)}] ✓")
                    except Exception as e:
                        print(f"  [{i+1}/{len(new_urls)}] ✗ {e}")

            browser.close()

    all_downloads = (old["downloads"] if old else []) + new_downloads

    with open("source.json", "w", encoding="utf-8") as f:
        json.dump({"name": "Game3RB", "downloads": all_downloads}, f, ensure_ascii=False, indent=2)

    print(f"Done! {len(all_downloads)} total ({len(new_downloads)} new).")

if __name__ == "__main__":
    main()   
