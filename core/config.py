import json 
from decouple import config


DEV_MODE = config('development', cast=bool)
PASSWORD = config('password')
WEBHOOK_URL = config('webhook_url')
MONGO = config('mongo') 
DOMAIN = 'kybr.tk' if not DEV_MODE else None
HOST = '127.0.0.1' if DEV_MODE else '0.0.0.0'
PORT = 8000 if DEV_MODE else 80