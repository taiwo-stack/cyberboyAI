import sys, asyncio
sys.path.insert(0, 'backend')
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path('backend/.env'))

async def diagnose():
    print('=== LOOKUP FEED DIAGNOSTICS ===')

    # 1. PhishTank Cache (Supabase table)
    from tools.supabase_client import supabase
    try:
        res = supabase.table('phishtank_cache').select('id', count='exact').execute()
        count = res.count or 0
        print(f'[1] PhishTank/URLhaus cache: {count} URLs stored in DB')
        if count == 0:
            print('    WARNING: Cache is empty. Scheduler may not have run yet.')
    except Exception as e:
        print(f'[1] PhishTank cache ERROR: {e}')

    # 2. AbuseIPDB - test with known bad IP
    from agents.lookup_agent import LookupAgent
    agent = LookupAgent()
    try:
        score = await agent.abuseipdb_check('http://185.220.101.1/')
        status = 'WORKING' if score > 50 else 'responded (low score or clean)'
        print(f'[2] AbuseIPDB test (185.220.101.1): score={score} -> {status}')
    except Exception as e:
        print(f'[2] AbuseIPDB ERROR: {e}')

    # 3. OTX - test with known flagged URL
    try:
        hit, pulses = await agent.otx_check('http://malware.wicar.org/data/ms14_064_ole_xp.html')
        status = 'WORKING' if hit else 'responded (not flagged in OTX)'
        print(f'[3] AlienVault OTX test: hit={hit}, pulses={pulses} -> {status}')
    except Exception as e:
        print(f'[3] OTX ERROR: {e}')

    # 4. Google Safe Browsing - Google official test malware URL
    from tools.safe_browsing import check_safe_browsing
    try:
        result = await check_safe_browsing('http://malware.testing.google.test/testing/malware/')
        is_mal = result['is_malicious']
        threats = result['threat_types']
        if is_mal:
            print(f'[4] Google Safe Browsing: WORKING -> threats={threats}')
        else:
            print(f'[4] Google Safe Browsing: returned clean on test URL - check API key or Safe Browsing API not enabled')
    except Exception as e:
        print(f'[4] Google Safe Browsing ERROR: {e}')

    print('=== END DIAGNOSTICS ===')

asyncio.run(diagnose())
