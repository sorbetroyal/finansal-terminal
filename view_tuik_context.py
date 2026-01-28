import requests

url = "https://www.tuik.gov.tr/Home/Index"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, headers=headers)
idx = r.text.find("TÜFE")
if idx != -1:
    print(r.text[idx-500:idx+1500])
