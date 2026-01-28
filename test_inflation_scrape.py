import requests
from bs4 import BeautifulSoup

def test_scrape_bloomberg():
    url = "https://www.bloomberght.com/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        # Look for inflation text
        text = soup.get_text()
        if "Enflasyon" in text:
            print("Found Enflasyon text!")
            # Try to find specific tags
            # BloombergHT usually has a top bar or a sidebar with macro data
            # Let's search for "TÜFE"
            if "TÜFE" in text:
                print("Found TÜFE text!")
                # Get a snippet
                idx = text.find("TÜFE")
                print(text[idx:idx+100])
        else:
            print("Enflasyon not found on homepage.")
    except Exception as e:
        print(f"Error: {e}")

test_scrape_bloomberg()
