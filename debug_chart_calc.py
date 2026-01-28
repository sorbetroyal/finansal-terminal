from utils import get_all_holdings, get_portfolio_history
import pandas as pd

def debug_chart_values():
    holdings = get_all_holdings()
    print(f"Total holdings: {len(holdings)}")
    
    # Simulate first portfolio or all
    hist_df = get_portfolio_history(holdings, period="1mo")
    
    if not hist_df.empty:
        print("\nHistorical Data Summary:")
        print(hist_df.tail())
        print(f"\nLast Market Value: {hist_df['Market_Value'].iloc[-1]:,.2f}")
        print(f"Last Total Cost: {hist_df['Total_Cost'].iloc[-1]:,.2f}")
        
        # Breakdown by columns in the intermediate steps? 
        # I can't see internal dicts, but I can check why it might be low.
    else:
        print("\nHist DF is EMPTY!")

debug_chart_values()
