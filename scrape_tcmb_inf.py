import requests
from bs4 import BeautifulSoup

url = "https://www.tcmb.gov.tr/wps/wcm/connect/tr/tcmb+tr/main+menu/istatistikler/enflasyon+verileri/tuketici+fiyatlari"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.content, 'html.parser')
# TCMB often has tables. Let's find tables.
tables = soup.find_all('table')
for i, table in enumerate(tables):
    print(f"TABLE {i}:")
    print(table.get_text()[:500])
