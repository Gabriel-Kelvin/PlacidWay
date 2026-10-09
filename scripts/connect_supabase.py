"""Secure local setup after the dedicated Free project and schema exist."""
import getpass
import re
from pathlib import Path
import httpx
from dotenv import set_key

def main():
    root=Path(__file__).resolve().parents[1]
    url=input('Dedicated Supabase project URL: ').strip().rstrip('/')
    if not re.fullmatch(r'https://[a-z0-9]+\.supabase\.co',url):
        raise SystemExit('Use the HTTPS URL of your dedicated Supabase project.')
    key=getpass.getpass('Server secret key (hidden; never use a browser/public key): ').strip()
    if not key.startswith(('sb_secret_','eyJ')):raise SystemExit('Expected a server secret or legacy service-role key.')
    try:
        headers={'apikey':key}
        if key.startswith('eyJ'):headers['Authorization']='Bearer '+key
        with httpx.Client(timeout=15,headers=headers) as client:
            for table in ['pw_events','pw_knowledge','pw_errors']:
                response=client.get(f'{url}/rest/v1/{table}',params={'select':'id','limit':'1'})
                response.raise_for_status()
    except Exception:
        raise SystemExit('Connection check failed. Apply supabase/schema.sql in the dedicated project and verify your server key. No credentials were saved.')
    path=root/'.env'
    if not path.exists():raise SystemExit('Run scripts/setup_secrets.py first.')
    set_key(str(path),'SUPABASE_URL',url);set_key(str(path),'SUPABASE_SECRET_KEY',key)
    print('Connection verified and saved locally. Restart the app. Writes go directly to Supabase. No key was displayed.')

if __name__=='__main__':main()
