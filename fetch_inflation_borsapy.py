import borsapy
try:
    cal = borsapy.EconomicCalendar()
    # Let's get events for the last month to find inflation
    events = cal.events(period="1mo")
    # Search for "Enflasyon" or "TÜFE"
    inf_events = events[events['Event'].str.contains("Enflasyon|TÜFE", case=False, na=False)]
    print(inf_events)
except Exception as e:
    print(f"Error: {e}")
