import borsapy

try:
    # Test with a well-known fund, e.g., TCD (Tacirler Portföy Değişken Fon)
    fund = borsapy.Fund("TCD")
    print("Fund Info Keys:")
    print(fund.info.keys())
    
    # Check if there is a method for content or portfolio
    print("\nDir(fund):")
    print([m for m in dir(fund) if not m.startswith("_")])
except Exception as e:
    print(f"Error: {e}")
