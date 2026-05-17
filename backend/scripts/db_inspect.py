import requests, os
from dotenv import load_dotenv

load_dotenv('backend/.env')
url = f"{os.getenv('SUPABASE_URL')}/rest/v1/"
headers = {
    'apikey': os.getenv('SUPABASE_SERVICE_KEY'),
    'Authorization': f"Bearer {os.getenv('SUPABASE_SERVICE_KEY')}",
    'Accept-Profile': 'public'
}
res = requests.get(url, headers=headers)
sub = res.json().get('definitions', {}).get('threat_submissions', {})
if sub:
    print('Columns for threat_submissions:')
    for prop in sub.get('properties', {}).keys():
        print(f' - {prop}')
else:
    print('threat_submissions not found in schema definitions')
