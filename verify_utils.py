from utils import is_gold_tl_asset

test_symbols = ["ALTIN", "ÇEYREK", "YARIM", "TAM", "ATA", "CEYREK", "ALTIN.S1"]
for s in test_symbols:
    print(f"{s}: {is_gold_tl_asset(s)}")
