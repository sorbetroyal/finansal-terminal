import requests
from bs4 import BeautifulSoup
import re

def get_inflation_from_tuik():
    # Attempting to search directly in TUIK bultens
    # The search page is https://data.tuik.gov.tr/Bulten/Search
    # But usually the category page has the latest
    url = "https://data.tuik.gov.tr/Kategori/GetKategori?p=Enflasyon-ve-Fiyat-106"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.content, 'html.parser')
        
        # Look for headlines
        bulletins = soup.find_all('a', href=re.compile(r"Bulten/Index"))
        for b in bulletins:
            title = b.get_text().strip()
            if "Tüketici Fiyat Endeksi" in title:
                link = "https://data.tuik.gov.tr" + b['href']
                print(f"Checking bulletin: {title}")
                
                r_b = requests.get(link, headers=headers, timeout=15)
                soup_b = BeautifulSoup(r_b.content, 'html.parser')
                text = soup_b.get_text()
                
                # Check for the magic keywords
                # "bir önceki yılın aynı ayına göre %30,89"
                # "bir önceki aya göre %0,89"
                annual = re.search(r"bir önceki yılın aynı ayına göre\s+%\s?(\d+,\d+)", text)
                monthly = re.search(r"bir önceki aya göre\s+%\s?(\d+,\d+)", text)
                
                if annual and monthly:
                    return {
                        "annual": annual.group(1).replace(",", "."),
                        "monthly": monthly.group(1).replace(",", "."),
                        "label": title
                    }
    except Exception as e:
        print(f"Error scraping TUIK: {e}")
    
    return None

if __name__ == "__main__":
    data = get_inflation_from_tuik()
    if data:
        print(f"RESULT: {data}")
    else:
        print("RESULT: NOT_FOUND")
