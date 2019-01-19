from decouple import config

DEV_MODE = config('development', cast=bool)
PASSWORD = SECRET = config('password')
WEBHOOK_URL = config('webhook_url')
NEW_INSTANCE_WEBHOOK_URL = config('new_instance_webhook_url', default=WEBHOOK_URL)
MONGO = config('mongo') 
DOMAIN = 'modmail.tk' if not DEV_MODE else 'example.com'
HOST = '127.0.0.1' if DEV_MODE else '0.0.0.0'
PORT = 6969 if DEV_MODE else 80

OLD_GITHUB_SECRET = config('old_github_secret')
GITHUB_SECRET = config('dev_github_secret', default=None) if DEV_MODE else config('github_secret')
GITHUB_CLIENT_ID = config('dev_github_client_id', default=None) if DEV_MODE else config('github_client_id') 
GITHUB_OAUTH_URL = 'https://github.com/login/oauth/authorize?'
GITHUB_REDIRECT_URL = f'http://{DOMAIN}/callback' if DEV_MODE else f'https://{DOMAIN}/callback'

API_BASE = f'http://api.{DOMAIN}' if DEV_MODE else f'https://api.{DOMAIN}'