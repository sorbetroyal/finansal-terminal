import requests
import re

url = "https://www.tuik.gov.tr/Home/Index"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, headers=headers)
# Let's find patterns like "Aralık 2025" or numbers following %
res = re.findall(r"(\d+,\d+)", r.text)
# This might return too many, but let's see if 30,89 is there
if "30,89" in r.text or "0,89" in r.text:
    print("Found the target numbers in raw text!")
else:
    print("Target numbers NOT found in raw text.")

# Looking for specific "monthly" and "annual" labels in Turkish
tufe_pos = r.text.find("Tüketici Fiyat Endeksi")
if tufe_pos != -1:
    print("Found Tüketici Fiyat Endeksi at:", tufe_pos)
    print(r.text[tufe_pos:tufe_pos+200])
