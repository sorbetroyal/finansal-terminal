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
        
        # Look for links containing "Tüketici Fiyat Endeksi"
        links = soup.find_all('a', text=re.compile("Tüketici Fiyat Endeksi", re.I))
        if not links:
            # Try finding by href or class if possible
            links = soup.find_all('a', href=re.compile("Bulten/Index", re.I))
        
        for link in links:
            if "Tüketici Fiyat Endeksi" in link.get_text():
                detail_url = "https://data.tuik.gov.tr" + link['href']
                print(f"Found bulletin: {link.get_text()} at {detail_url}")
                
                # Now go to the bulletin page
                res_detail = requests.get(detail_url, headers=headers, timeout=10)
                soup_detail = BeautifulSoup(res_detail.content, 'html.parser')
                text = soup_detail.get_text()
                
                # Look for patterns like "% 0,89" and "% 30,89"
                # Usually TUIK bulletins have a summary table or sentence
                # "TÜFE'deki (2003=100) değişim ... bir önceki aya göre %0,89, bir önceki yılın aynı ayına göre %30,89"
                
                monthly = re.search(r"bir önceki aya göre %\s?(\d+,\d+)", text)
                annual = re.search(r"bir önceki yılın aynı ayına göre %\s?(\d+,\d+)", text)
                
                if monthly and annual:
                    return {
                        "monthly": monthly.group(1),
                        "annual": annual.group(1),
                        "source": detail_url
                    }
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    data = get_tuik_inflation()
    print(data)
