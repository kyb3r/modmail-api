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
app.blueprint(core.modmail)

app.static('/static', './static')

@app.listener('before_server_start')
async def init(app, loop):
    '''Initialize app config, database and send the status discord webhook payload.'''
    app.password = config.PASSWORD
    app.session = aiohttp.ClientSession(loop=loop)
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

@app.get('/logged-in')
async def logged_in(request):
    username = request.raw_args.get('username', 'there')
    with open('static/template.html') as f:
        html = f.read().format(
            title=f'Hey {username}!',
            message='You can now go back to discord and use the `<code>update</code>` command.'
        )
    return response.html(html)

@app.get('/already-logged-in')
async def already_logged_in(request):
    with open('static/template.html') as f:
        html = f.read().format(
            title='Already Logged In!',
            message='Please use the `<code>github logout</code>` command and logout first.'
        )
    return response.html(html)

if __name__ == '__main__':
    app.run(host=config.HOST, port=config.PORT)
