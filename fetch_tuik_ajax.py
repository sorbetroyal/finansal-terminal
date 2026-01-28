import requests
import json

def get_tuik_bultens():
    url = "https://data.tuik.gov.tr/Bulten/GetBultenler?p=106&y=2025&d=1"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print("Status:", r.status_code)
        print("Content Snippet:", r.text[:1000])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_tuik_bultens()
