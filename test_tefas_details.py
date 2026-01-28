import borsapy
fund = borsapy.Fund("TCD")
alloc = fund.allocation
print("Cols:", alloc.columns.tolist())
print("Latest Data:")
print(alloc.tail(5))
