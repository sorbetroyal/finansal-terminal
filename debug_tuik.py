import requests
url = "https://data.tuik.gov.tr/Kategori/GetKategori?p=Enflasyon-ve-Fiyat-106"
headers = {"User-Agent": "Mozilla"}
r = requests.get(url, headers=headers)
print(r.text[:2000])
