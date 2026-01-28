from utils import add_asset

# Adding sample data
# THY at 250 TL
add_asset("THYAO.IS", 100, 250.0)
# USD at 30 TL
add_asset("USDTRY=X", 1000, 30.0)
# Gold (Ons) at 2000 USD (roughly)
add_asset("GC=F", 1, 2030.0)

print("Sample data added successfully.")
