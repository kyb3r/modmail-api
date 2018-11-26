import os
import hmac
import hashlib
import json
import socket
import traceback

from sanic import Sanic, response
from sanic.exceptions import SanicException
import aiohttp
import dhooks


with open('config.json') as f:
    config = json.load(f)

app = Sanic(__name__)
app.static('/static', './static')

dev_mode = bool(int(config.get('development')))
domain = None if dev_mode else config.get('domain')
URL = f'https://{domain}' if domain else None

class Color:
    green = 0x2ecc71
    red = 0xe74c3c
    orange = 0xe67e22

def log_server_start():
    em = dhooks.Embed(color=Color.green)
    em.set_author('[INFO] Starting Worker', url=URL)
    em.set_footer(f'Hostname: {socket.gethostname()} | Domain: {domain}')
    return app.webhook.send(embeds=em)

def log_server_stop():
    em = dhooks.Embed(color=Color.red)
    em.set_footer(f'Hostname: {socket.gethostname()} | Domain: {domain}')
    em.set_author('[INFO] Server Stopped')
    return app.webhook.send(embeds=em)

def log_server_update():
    em = dhooks.Embed(color=Color.orange)
    em.set_footer(f'Hostname: {socket.gethostname()} | Domain: {domain}')
    em.set_author('[INFO] Server updating and restarting.')
    return app.webhook.send(embeds=em)

def log_server_error(excstr):
    em = dhooks.Embed(color=Color.red)
    em.set_author('[ERROR] Exception occured on server')
    em.description = f'```py\n{excstr}```'
    em.set_footer(f'Hostname: {socket.gethostname()} | Domain: {domain}')
    return app.webhook.send(embeds=em)

@app.exception(SanicException)
async def sanic_exception(request, exception):
    try:
        raise(exception)
    except:
        traceback.print_exc()
    return response.text(str(exception), status=exception.status_code)

@app.exception(Exception)
async def on_error(request, exception):
    if not isinstance(exception, SanicException):
        try:
            raise(exception)
        except:
            excstr = traceback.format_exc()
            print(excstr)
            
        if len(excstr) > 1000:
            excstr = excstr[:1000] 

        app.add_task(log_server_error(excstr))
    return response.text('something went wrong xd', status=500)

@app.listener('before_server_start')
async def init(app, loop):
    '''Initialize app config, database and send the status discord webhook payload.'''
    app.password = config.get('password')
    app.session = aiohttp.ClientSession(loop=loop)
    url = config.get('webhook_url')
    app.webhook = dhooks.Webhook.Async(url)
    app.webhook.avatar_url = 'http://icons.iconarchive.com/icons/graphicloads/100-flat/256/analytics-icon.png'
    app.webhook.username = 'kybr.tk'
    await log_server_start()

@app.listener('after_server_stop')
async def aexit(app, loop):
    await log_server_stop()
    await app.session.close()

@app.get('/', host=domain)
async def index(request):
    with open('static/index.html') as f:
        return response.html(f.read())

@app.get('/', host=f'discord.{domain}')
async def discord(request):
    return response.redirect('https://discord.gg/etJNHCQ')

@app.get('/source', host=domain)
async def source(request):
    return response.redirect('https://github.com/kyb3r/webserver')

@app.get('/<repo>', host=f'repo.{domain}')
async def repo(request, repo):
    return response.redirect(f'https://github.com/kyb3r/{repo}')

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
    await log_server_update()
    await log_server_stop()
    await app.session.close()
    command = 'git pull && pm2 restart webserver'
    os.system(f'echo {app.password}|sudo -S {command}')

app.run(host='127.0.0.1' if dev_mode else '0.0.0.0', port=8000 if dev_mode else 80)