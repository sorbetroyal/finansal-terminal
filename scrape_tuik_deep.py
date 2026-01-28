import requests
from bs4 import BeautifulSoup
import re

def scrape_tuik_category():
    url = "https://data.tuik.gov.tr/Kategori/GetKategori?p=Enflasyon-ve-Fiyat-106"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.content, 'html.parser')
        # TUIK categorizes bulletins under "Haber Bültenleri"
        # Let's find any text with "Tüketici Fiyat Endeksi"
        items = soup.find_all(string=re.compile("Tüketici Fiyat Endeksi", re.I))
        for item in items:
            parent = item.parent
            if parent.name == 'a' and 'href' in parent.attrs:
                href = parent['href']
                if "Bulten/Index" in href:
                    full_url = "https://data.tuik.gov.tr" + href
                    print(f"LATEST LINK: {full_url}")
                    # Scrape this link
                    r2 = requests.get(full_url, headers=headers)
                    soup2 = BeautifulSoup(r2.content, 'html.parser')
                    text = soup2.get_text()
                    # Look for the percentages
                    m = re.search(r"bir önceki aya göre\s+%\s?(\d+,\d+)", text)
                    a = re.search(r"bir önceki yılın aynı ayına göre\s+%\s?(\d+,\d+)", text)
                    if m or a:
                        print(f"MONTHLY: {m.group(1) if m else '?'}, ANNUAL: {a.group(1) if a else '?'}")
                        return
        print("No bulletin links found with current scrape logic.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    scrape_tuik_category()
