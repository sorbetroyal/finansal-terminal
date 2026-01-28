from utils import supabase
import json

try:
    res = supabase.table("alerts").select("*").execute()
    print("Supabase Alerts:")
    print(json.dumps(res.data, indent=2))
except Exception as e:
    print(f"Supabase Error: {e}")
