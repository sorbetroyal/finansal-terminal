import requests
from bs4 import BeautifulSoup
import re

def scrape_trthaber():
    url = "https://www.trthaber.com/haber/ekonomi/"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.content, 'html.parser')
        text = soup.get_text()
        # Look for headlines about inflation
        # "Enflasyon rakamları açıklandı" etc.
        # This is hard to get the exact % without opening the article.
        pass
    except:
        pass

if __name__ == "__main__":
    scrape_trthaber()
