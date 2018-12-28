from decouple import config

DEV_MODE = config('development', cast=bool)
PASSWORD = config('password')
DOMAIN = config('domain')
WEBHOOK_URL = 'https://discordapp.com/api/webhooks/516452309107212328/2fcVFuW4lMDDdanhJATcwxd2BzcddN-_7ov9xwVP01ppSbh5SIB2hhYexCGeDY4QEKPY' #config('webhook_url')
MONGO = config('mongo')

HEROKU_SECRET = config('heroku_secret')
GITHUB_SECRET = config('github_secret')
