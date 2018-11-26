import os
import json
import traceback

from sanic import Sanic, response
from sanic.exceptions import SanicException

import aiohttp
import dhooks

import core
from core.config import Config

app = Sanic(__name__)
app.cfg = config = Config.from_json('config.json')
app.static('/static', './static')

app.blueprint(core.api)
app.blueprint(core.rd)

@app.listener('before_server_start')
async def init(app, loop):
    '''Initialize app config, database and send the status discord webhook payload.'''
    app.password = config.password
    app.session = aiohttp.ClientSession(loop=loop)
    app.webhook = dhooks.Webhook.Async(config.webhook_url)
    app.webhook.avatar_url = 'http://icons.iconarchive.com/icons/graphicloads/100-flat/256/analytics-icon.png'
    app.webhook.username = 'kybr.tk'
    await core.log_server_start(app)

@app.listener('after_server_stop')
async def aexit(app, loop):
    await core.log_server_stop(app)
    await app.session.close()

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

        app.add_task(core.log_server_error(excstr))
    return response.text('something went wrong xd', status=500)

@app.get('/', host=config.domain)
async def index(request):
    with open('static/index.html') as f:
        return response.html(f.read())

if __name__ == '__main__':
    host = '127.0.0.1' if config.development else '0.0.0.0'
    port = 8000 if config.development else 80
    app.run(host=host, port=port)