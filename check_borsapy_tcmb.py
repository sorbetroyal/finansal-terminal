import borsapy
try:
    print("borsapy.tcmb dir:", [m for m in dir(borsapy.tcmb) if not m.startswith("_")])
except Exception as e:
    print(e)
