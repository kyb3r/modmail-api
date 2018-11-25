import os
from sanic import Sanic, response
import aiohttp
import dhooks
import hmac
import hashlib
import json

with open('config.json') as f:
    config = json.load(f)

app = Sanic(__name__)
dev_mode = bool(int(config.get('development')))
domain = None if dev_mode else config.get('domain')

@app.listener('before_server_start')
async def init(app, loop):
    '''Initialize app config, database and send the status discord webhook payload.'''
    app.password = config.get('password')
    app.session = aiohttp.ClientSession(loop=loop)
    url = config.get('webhook_url')
    app.webhook = dhooks.Webhook.Async(url)

def production_route(*args, **kwargs): # subdomains dont exist on localhost.
    def decorator(func):
        return func if dev_mode else app.route(*args, **kwargs)(func)
    return decorator

app.static('/static', './static')

@production_route('/')
async def wildcard(request):
    return response.text(f'Hello there, this subdomain doesnt do anything yet. ({request.host})')

@app.get('/', host=domain)
async def index(request):
    with open('static/index.html') as f:
        return response.html(f.read())

def fbytes(s, encoding='utf-8', strings_only=False, errors='strict'):
    # Handle the common case first for performance reasons.
    if isinstance(s, bytes):
        return s
    if isinstance(s, memoryview):
        return bytes(s)
    else:
        return s.encode(encoding, errors)

def validate_github_payload(request):
    if not request.headers.get('X-Hub-Signature'):
        return False
    sha_name, signature = request.headers['X-Hub-Signature'].split('=')
    digester = hmac.new(
        fbytes(request.app.password), 
        fbytes(request.body),
        hashlib.sha1
        )
    generated = fbytes(digester.hexdigest())
    return hmac.compare_digest(generated, fbytes(signature))

@app.post('/hooks/github', host=domain)
async def upgrade(request):
    if not validate_github_payload(request):
        return response.text('fuck off', 401) # not sent by github
    app.loop.create_task(restart_later())
    return response.json({'success': True})

async def restart_later():
    await app.session.close()
    command = 'sh ../webserver.sh'
    os.system(f'echo {app.password}|sudo -S {command}')

app.run(host='0.0.0.0', port=8000 if dev_mode else 80)