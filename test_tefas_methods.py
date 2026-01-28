import borsapy
fund = borsapy.Fund("TCD")
print("METOTLAR:", [m for m in dir(fund) if not m.startswith("_")])
