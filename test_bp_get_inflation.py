import borsapy as bp

try:
    print("Testing bp.get_inflation()...")
    inflation_data = bp.get_inflation() 
    print("SUCCESS:")
    print(inflation_data)
except AttributeError:
    print("ERROR: borsapy has no attribute 'get_inflation'")
except Exception as e:
    print(f"ANOTHER ERROR: {e}")
