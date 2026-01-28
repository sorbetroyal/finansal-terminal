import requests
from bs4 import BeautifulSoup
import re

def get_latest_tuik_inflation():
    url = "https://data.tuik.gov.tr/Kategori/GetKategori?p=Enflasyon-ve-Fiyat-106"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.content, 'html.parser')
        links = soup.find_all('a', href=re.compile("Bulten/Index"))
        for l in links:
            if "Tüketici Fiyat Endeksi" in l.get_text():
                detail_url = "https://data.tuik.gov.tr" + l['href']
                print(f"Found: {detail_url}")
                r2 = requests.get(detail_url, headers=headers)
                soup2 = BeautifulSoup(r2.content, 'html.parser')
                text = soup2.get_text()
                monthly = re.search(r"bir önceki aya göre\s+%\s?(\d+,\d+)", text)
                annual = re.search(r"bir önceki yılın aynı ayına göre\s+%\s?(\d+,\d+)", text)
                if monthly and annual:
                    return {"annual": annual.group(1), "monthly": monthly.group(1), "found": True}
    except Exception as e:
        print(e)
    return {"annual": "31,00", "monthly": "0,89", "found": False}

if __name__ == "__main__":
    print(get_latest_tuik_inflation())
