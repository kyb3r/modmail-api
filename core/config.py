from decouple import config


DEV_MODE = config('development', cast=bool)
PASSWORD = config('password')
WEBHOOK_URL = config('webhook_url')
MONGO = config('mongo') 
DOMAIN = 'modmail.tk' if not DEV_MODE else 'example.com'
HOST = '127.0.0.1' if DEV_MODE else '0.0.0.0'
PORT = 6969 if DEV_MODE else 80

HEROKU_SECRET = config('heroku_secret')
GITHUB_SECRET = config('github_secret')
