import borsapy
fund = borsapy.Fund("TCD")
try:
    alloc = fund.allocation
    print("Allocation Data:")
    print(alloc)
except Exception as e:
    print(f"Error: {e}")
