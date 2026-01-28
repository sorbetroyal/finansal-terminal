from utils import get_current_data
import json

def test():
    # Simulate the button click call
    symbol = "ALTIN.S1"
    a_type = "bist hisse"
    print(f"Testing {symbol} as {a_type}...")
    data = get_current_data(symbol, a_type)
    print(f"Result: {json.dumps(data)}")

    # Simulate with .IS anyway
    symbol_is = "ALTIN.S1.IS"
    print(f"Testing {symbol_is} as {a_type}...")
    data_is = get_current_data(symbol_is, a_type)
    print(f"Result: {json.dumps(data_is)}")

test()
