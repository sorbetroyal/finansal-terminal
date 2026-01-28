import requests
from bs4 import BeautifulSoup
import re

def get_tuik_inflation():
    url = "https://data.tuik.gov.tr/Kategori/GetKategori?p=Enflasyon-ve-Fiyat-106"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for links in the category page
        # TUIK usually lists bulletins in a list or table
        all_links = soup.find_all('a')
        bulletin_link = None
        for a in all_links:
            txt = a.get_text().strip()
            if "Tüketici Fiyat Endeksi" in txt and "Aralık" in txt: # Looking for the latest
                bulletin_link = a['href']
                print(f"Candidate: {txt} -> {bulletin_link}")
                break
        
        if not bulletin_link:
            # Fallback: find any Bulten/Index link
            for a in all_links:
                if "Bulten/Index" in a.get( 'href', ''):
                    txt = a.get_text().strip()
                    if "Tüketici Fiyat Endeksi" in txt:
                        bulletin_link = a['href']
                        print(f"Fallback candidate: {txt} -> {bulletin_link}")
                        break
        
        if bulletin_link:
            if not bulletin_link.startswith("http"):
                bulletin_link = "https://data.tuik.gov.tr" + bulletin_link
            
            res_detail = requests.get(bulletin_link, headers=headers, timeout=10)
            soup_detail = BeautifulSoup(res_detail.content, 'html.parser')
            text = soup_detail.get_text()
            
            # Look for monthly increase
            # bir önceki aya göre %0,89
            monthly = re.search(r"bir önceki aya göre\s+%\s?(\d+,\d+)", text)
            # bir önceki yılın aynı ayına göre %30,89
            annual = re.search(r"bir önceki yılın aynı ayına göre\s+%\s?(\d+,\d+)", text)
            
            if monthly or annual:
                return {
                    "monthly": monthly.group(1) if monthly else "N/A",
                    "annual": annual.group(1) if annual else "N/A",
                    "source": bulletin_link
                }
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    data = get_tuik_inflation()
    print(data)
