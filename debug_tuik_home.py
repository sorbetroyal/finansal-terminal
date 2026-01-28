import requests
import re

def get_tuik_dashboard():
    url = "https://www.tuik.gov.tr/Home/Index"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        # TUIK homepage often has a script or data object with macro stats
        # Search for TÜFE in the raw HTML
        content = r.text
        # Search for something like: "TÜFE","pay":"30,89" or similar
        print("TÜFE index in HTML:", content.find("TÜFE"))
        # Looking for numbers near "TÜFE"
        snippet = re.findall(r"TÜFE.*?(\d+,\d+)", content, re.S)
        print("Snippet nearby:", snippet)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    get_tuik_dashboard()
