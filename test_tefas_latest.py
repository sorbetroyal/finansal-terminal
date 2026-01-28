import borsapy
fund = borsapy.Fund("TCD")
alloc = fund.allocation
latest_date = alloc['Date'].max()
latest_alloc = alloc[alloc['Date'] == latest_date]
print(f"Latest Date: {latest_date}")
print(latest_alloc[['asset_type', 'weight']])
