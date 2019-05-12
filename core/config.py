from decouple import config

DEV_MODE = config('development', cast=bool)
PASSWORD = SECRET = config('password')
WEBHOOK_URL = config('webhook_url')
NEW_INSTANCE_WEBHOOK_URL = config('new_instance_webhook_url', default=WEBHOOK_URL)
MONGO = config('mongo') 
DOMAIN = 'modmail.tk' if not DEV_MODE else 'example.com'
HOST = '127.0.0.1' if DEV_MODE else '0.0.0.0'
PORT = 6969 if DEV_MODE else 80

API_BASE = f'http://api.{DOMAIN}' if DEV_MODE else f'https://api.{DOMAIN}'