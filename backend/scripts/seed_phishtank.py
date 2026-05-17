import asyncio
import os
import sys
import httpx
import csv
import zlib
from datetime import datetime

# Add the parent directory to sys.path to allow importing tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.supabase_client import supabase

OPENPHISH_URL = "https://openphish.com/feed.txt"
URLHAUS_URL = "https://urlhaus.abuse.ch/downloads/csv_recent/"

async def fetch_openphish():
    print("[*] Downloading from OpenPhish...")
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(OPENPHISH_URL)
        if response.status_code != 200:
            print(f"[!] Failed to fetch OpenPhish: {response.status_code}")
            return []
        
        urls = response.text.strip().split('\n')
        records = []
        for url in urls:
            if not url.strip(): continue
            # Generate deterministic BIGINT id using zlib.crc32
            url_id = zlib.crc32(url.encode())
            records.append({
                "id": url_id,
                "url": url,
                "verified": True,
                "target_brand": None,
                "added_at": datetime.now().isoformat()
            })
        return records

async def fetch_urlhaus():
    print("[*] Downloading from URLhaus...")
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(URLHAUS_URL)
        if response.status_code != 200:
            print(f"[!] Failed to fetch URLhaus: {response.status_code}")
            return []
        
        # Parse CSV
        lines = response.text.splitlines()
        # Filter out comments starting with #
        csv_lines = [line for line in lines if not line.startswith('#')]
        
        reader = csv.DictReader(csv_lines, fieldnames=[
            "id", "dateadded", "url", "url_status", "last_online", "threat", "tags", "urlhaus_link", "reporter"
        ])
        
        records = []
        for row in reader:
            if row["url_status"] == "online":
                records.append({
                    "id": int(row["id"]),
                    "url": row["url"],
                    "verified": True,
                    "target_brand": None,
                    "added_at": row["dateadded"]
                })
        return records

async def seed_phishtank():
    print("[*] Starting PhishTank cache seeding...")
    
    openphish_records = await fetch_openphish()
    urlhaus_records = await fetch_urlhaus()
    
    all_records = openphish_records + urlhaus_records
    total_found = len(all_records)
    print(f"[*] Total records to sync: {total_found} (OpenPhish: {len(openphish_records)}, URLhaus: {len(urlhaus_records)})")
    
    # Batch upsert in chunks of 100
    batch_size = 100
    for i in range(0, total_found, batch_size):
        batch = all_records[i:i+batch_size]
        try:
            supabase.table("phishtank_cache").upsert(batch, on_conflict="id").execute()
            print(f"[+] Synced batch {i//batch_size + 1}/{(total_found // batch_size) + 1}")
        except Exception as e:
            print(f"[!] Error syncing batch starting at {i}: {e}")
            
    print(f"[+] Sync complete. Total: {total_found}")

if __name__ == "__main__":
    asyncio.run(seed_phishtank())
