from urllib.parse import urlencode, parse_qs
import traceback
import datetime
import secrets
import socket

from motor.motor_asyncio import AsyncIOMotorClient
from jinja2 import Environment, PackageLoader
from sanic import Sanic, response
from sanic.exceptions import SanicException
from sanic_session import Session, InMemorySessionInterface

import aiohttp
import dhooks

from core import config
import core


app = Sanic(__name__)

app.cfg = config
Session(app, interface=InMemorySessionInterface(domain=config.DOMAIN))

app.blueprint(core.api)
app.blueprint(core.rd)

app.static('/static', './static')

app.static('/favicon.ico', './static/favicon.ico')


jinja_env = Environment(loader=PackageLoader('app', 'templates'))


def render_template(name, *args, **kwargs):
    template = jinja_env.get_template(name + '.html')
    request = core.get_stack_variable('request')
    kwargs['request'] = request
    kwargs['session'] = request['session']
    kwargs['user'] = request['session'].get('user')
    kwargs.update(globals())
    return response.html(template.render(*args, **kwargs))


app.render_template = render_template


@app.listener('before_server_start')
async def init(app, loop):
    """Initialize app config, database and send the status discord webhook payload."""
    app.password = config.PASSWORD
    app.session = aiohttp.ClientSession(loop=loop)
    app.webhook = dhooks.Webhook.Async(config.WEBHOOK_URL)
    app.new_instance_webhook = dhooks.Webhook.Async(config.NEW_INSTANCE_WEBHOOK_URL)
    app.webhook.avatar_url = 'http://icons.iconarchive.com/icons/graphicloads/100-flat/256/analytics-icon.png'
    app.webhook.username = 'modmail.tk'
    app.db = AsyncIOMotorClient(config.MONGO).modmail

    await core.log_server_start(app)


@app.listener('after_server_stop')
async def aexit(app, loop):
    await core.log_server_stop(app)
    await app.session.close()


@app.exception(SanicException)
async def sanic_exception(request, exception):

    resp = {
        'success': False,
        'error': str(exception)
    }

    print(exception)

    return response.json(resp, status=exception.status_code)


@app.exception(Exception)
async def on_error(request, exception):

    resp = {
        'success': False,
        'error': str(exception)
    }

    try:
        raise exception
    except:
        excstr = traceback.format_exc()
        print(excstr)

    if len(excstr) > 1800:
        excstr = excstr[:1800]

    em = dhooks.Embed(color=0xe74c3c, title=f'`[ERROR] - {request.method} {request.url}`')
    em.description = f'```py\n{excstr}```'
    em.set_footer(f'Host: {socket.gethostname()} | Domain: {app.cfg.DOMAIN}')

    app.add_task(app.webhook.send(embeds=[em]))

    return response.json(resp, status=500)


@app.get('/')
async def index(request):
    return render_template(
        'index',
        title='Modmail',
        message='DM to contact mods!'
    )

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=1234)
