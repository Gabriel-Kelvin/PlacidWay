import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
QUOTE_URL = 'https://www.placidway.com/request-info'
USER_AGENT = 'PlacidWayAssessmentBot/1.0 (+allowlisted assessment; contact via PlacidWay)'
MODEL = os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b')
RETENTION = int(os.getenv('RETENTION_DAYS', '30'))
