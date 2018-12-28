import traceback

from sanic import Sanic, response
from sanic.exceptions import SanicException

import aiohttp
import dhooks
from motor.motor_asyncio import AsyncIOMotorClient

import core
from core import config

app = Sanic(__name__)
app.cfg = config

app.blueprint(core.api)
app.blueprint(core.rd)

app.static('/static', './static')

@app.listener('before_server_start')
async def init(app, loop):
    '''Initialize app config, database and send the status discord webhook payload.'''
    app.password = config.PASSWORD
    app.session = aiohttp.ClientSession(loop=loop)
    print(config.WEBHOOK_URL)
    app.webhook = dhooks.Webhook.Async(config.WEBHOOK_URL)
    app.webhook.avatar_url = 'http://icons.iconarchive.com/icons/graphicloads/100-flat/256/analytics-icon.png'
    app.webhook.username = 'kybr.tk'
    app.db = AsyncIOMotorClient(config.MONGO).modmail

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

        app.add_task(core.log_server_error(app, excstr))
    return response.text('something went wrong xd', status=500)

@app.get('/', host=config.DOMAIN)
async def index(request):
    return await response.file('static/index.html')

@app.get('/generative-artwork', host=config.DOMAIN)
async def genetics(request):
    return await response.file('static/generative.html')

if __name__ == '__main__':
    host = '127.0.0.1' if config.DEV_MODE else '0.0.0.0'
    port = 8000 if config.DEV_MODE else 80
    app.run(host=host, port=port)
