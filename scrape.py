import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime

BASE_URL = "https://game3rb.com/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_all_games():
    all_urls = []
    page = 1
    while True:
        url = f"{BASE_URL}page/{page}/" if page > 1 else BASE_URL
        resp = requests.get(url, timeout=30, headers=HEADERS)
        if resp.status_code != 200:
            break
        soup = BeautifulSoup(resp.text, "html.parser")
        links = soup.select("a.game-link")  # ← adapte ce sélecteur
        if not links:
            break
        all_urls.extend([a["href"] for a in links])
        print(f"  Page {page}: {len(links)} jeux")
        page += 1
        time.sleep(2)
    return all_urls

def scrape_game(url):
    full = url if url.startswith("http") else BASE_URL + url
    resp = requests.get(full, timeout=30, headers=HEADERS)
    if resp.status_code != 200:
        return None
    soup = BeautifulSoup(resp.text, "html.parser")
    title = soup.select_one("h1")
    magnet = soup.select_one("a[href^='magnet:']")
    size = soup.select_one(".file-size")
    date = soup.select_one(".upload-date")
    if not title or not magnet:
        return None
    return {
        "title": title.get_text(strip=True),
        "fileSize": size.get_text(strip=True) if size else "Unknown",
        "uris": [magnet["href"]],
        "uploadDate": date.get_text(strip=True) if date else datetime.utcnow().strftime("%Y-%m-%d")
    }

def main():
    urls = fetch_all_games()
    print(f"Found {len(urls)} games")
    downloads = []
    for i, u in enumerate(urls):
        try:
            d = scrape_game(u)
            if d:
                downloads.append(d)
                print(f"  [{i+1}/{len(urls)}] ✓ {d['title']}")
        except Exception as e:
            print(f"  [{i+1}/{len(urls)}] ✗ {e}")
        time.sleep(1)
    with open("source.json", "w", encoding="utf-8") as f:
        json.dump({"name": "Game3RB", "downloads": downloads}, f, ensure_ascii=False, indent=2)
    print(f"Done! {len(downloads)} entries.")

if __name__ == "__main__":
    main()   
