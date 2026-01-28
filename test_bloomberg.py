import requests
from bs4 import BeautifulSoup
import re

def scrape_bloomberg_macro():
    url = "https://www.bloomberght.com/ekonomi"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.content, 'html.parser')
        text = soup.get_text()
        # Search for "TÜFE" or "Enflasyon" near numbers
        # Usually Bloomberg has news like "Enflasyon yıllık %30,89 oldu"
        matches = re.findall(r"enflasyon.*?%\s?(\d+,\d+)", text, re.I)
        print("Matches:", matches)
    except:
        pass

if __name__ == "__main__":
    scrape_bloomberg_macro()
