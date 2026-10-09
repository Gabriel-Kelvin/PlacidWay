"""Initialize missing local secrets without printing or overwriting existing values."""
import secrets
from pathlib import Path
from dotenv import dotenv_values, set_key
root=Path(__file__).resolve().parents[1]
path=root/'.env'
if not path.exists():path.write_text((root/'.env.example').read_text(encoding='utf-8'),encoding='utf-8')
values=dotenv_values(path)
for key,value in {'ADMIN_PASSWORD':secrets.token_urlsafe(24),'SESSION_SECRET':secrets.token_hex(32)}.items():
    if not values.get(key):set_key(str(path),key,value)
print('Missing local secrets initialized. Existing values preserved. Add your Groq key to .env.')
