import borsapy

print("Testing borsapy.hisse...")
try:
    # Most likely it's a module with functions
    # data = borsapy.hisse.Hisse("THYAO").get_data()
    # Or just a function
    # Let's check dir(borsapy.hisse)
    import borsapy.hisse as hisse
    print("Methods in hisse:", dir(hisse))
    
    # Let's also check ticker
    import borsapy.ticker as ticker
    print("Methods in ticker:", dir(ticker))
    
except Exception as e:
    print(f"Error: {e}")
