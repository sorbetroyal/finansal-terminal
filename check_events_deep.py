import borsapy
import pandas as pd
from datetime import datetime, timedelta

try:
    cal = borsapy.EconomicCalendar()
    # Let's get 3 months to be safe
    end = datetime.now()
    start = end - timedelta(days=90)
    # The signature might be different, let's check help again
    # cal.events(period="1w") was in help
    events = cal.events(period="3mo")
    if not events.empty:
        # Save to CSV to inspect all events
        events.to_csv("all_events.csv", index=False)
        print(f"Total events found: {len(events)}")
        # Search for inflation keywords
        search_terms = ["Enflasyon", "TÜFE", "CPI", "Inflation"]
        found = events[events['Event'].str.contains("|".join(search_terms), case=False, na=False)]
        print("Inflation events found:")
        print(found)
    else:
        print("No events found in 3mo.")
except Exception as e:
    print(f"Error: {e}")
