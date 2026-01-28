import borsapy
import pandas as pd
from datetime import datetime, timedelta

def find_inflation():
    try:
        cal = borsapy.EconomicCalendar()
        # Turkish inflation is usually announced 3rd of every month.
        # Let's get the last 60 days to find December and January releases.
        events = cal.events(period="3mo")
        if not events.empty:
            # Filter for Turkey
            tr_events = events[events['Country'].str.contains("TÃ¼rkiye|Turkey|Türkiye", case=False, na=True)]
            # Filter for Inflation/TÜFE/CPI
            search_terms = ["Enflasyon", "TÜFE", "CPI", "Inflation", "Fiyat Endeksi"]
            inf = tr_events[tr_events['Event'].str.contains("|".join(search_terms), case=False, na=False)]
            
            if not inf.empty:
                print("LATEST INFLATION EVENTS FOUND:")
                print(inf[['Date', 'Event', 'Actual', 'Previous', 'Period']])
                return inf.to_dict(orient='records')
            else:
                print("No inflation events found in the list.")
                print("Available Events in Turkey:")
                print(tr_events['Event'].unique())
        else:
            print("No events returned at all.")
    except Exception as e:
        print(f"Error: {e}")
    return None

if __name__ == "__main__":
    find_inflation()
