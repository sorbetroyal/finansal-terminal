import json
import os
from datetime import datetime

ALERTS_FILE = r"c:\Users\yilma\OneDrive\Desktop\borsaveri\alerts.json"

if os.path.exists(ALERTS_FILE):
    with open(ALERTS_FILE, "r", encoding="utf-8") as f:
        alerts = json.load(f)
    
    changed = False
    used_ids = set()
    for i, alert in enumerate(alerts):
        # If ID is missing or duplicate, give a new one
        if "id" not in alert or alert["id"] in used_ids:
            alert["id"] = int(datetime.now().timestamp() * 1000) + i
            changed = True
        used_ids.add(alert["id"])
    
    if changed:
        with open(ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(alerts, f, ensure_ascii=False, indent=2)
        print("Alert IDs cleaned up.")
    else:
        print("No cleanup needed.")
else:
    print("Alerts file not found.")
