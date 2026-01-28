import borsapy
import pandas as pd

print("Checking borsapy for inflation/CPI...")
# Let's search for keywords in borsapy modules
try:
    print("Borsapy dir:", [m for m in dir(borsapy) if not m.startswith("_")])
except Exception as e:
    print(e)

# Maybe it's in a sub-module or specific class
try:
    # Most likely place: a function like get_inflation or similar
    # Let's try common names
    indicators = ["CPI", "TÜFE", "Inflation", "Enflasyon"]
    # Based on search result [6], it might be direct
except:
    pass
