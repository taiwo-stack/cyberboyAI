import asyncio
from tools.supabase_client import supabase

def clear_cache():
    try:
        # We delete anything containing "dhl-customs-fee.com"
        res = supabase.table("threat_submissions").delete().like("raw_input", "%dhl-customs-fee.com%").execute()
        print(f"Deleted rows: {res.data}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    clear_cache()
