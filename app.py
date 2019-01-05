from urllib.parse import urlencode, parse_qs
import traceback
import datetime
import asyncio
import secrets

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
app.blueprint(core.logs)
app.blueprint(core.dashboard)

app.blueprint(core.rd)
app.blueprint(core.deprecated)

app.static('/static', './static')

jinja_env = Environment(loader=PackageLoader('app', 'templates'))

def render_template(name, *args, **kwargs):
    template = jinja_env.get_template(name+'.html')
    request = core.get_stack_variable('request')
    kwargs['request'] = request
    kwargs['session'] = request['session']
    kwargs['user'] = request['session'].get('user')
    kwargs.update(globals())
    return response.html(template.render(*args, **kwargs))

app.render_template = render_template

@app.listener('before_server_start')
async def init(app, loop):
    '''Initialize app config, database and send the status discord webhook payload.'''
    app.password = config.PASSWORD
    app.session = aiohttp.ClientSession(loop=loop)
    app.webhook = dhooks.Webhook.Async(config.WEBHOOK_URL)
    app.webhook.avatar_url = 'http://icons.iconarchive.com/icons/graphicloads/100-flat/256/analytics-icon.png'
    app.webhook.username = 'modmail.tk'
    app.db = AsyncIOMotorClient(config.MONGO).modmail

    await core.log_server_start(app)

@app.listener('after_server_stop')
async def aexit(app, loop):
    await core.log_server_stop(app)
    await app.session.close()

@app.exception(SanicException)
def sanic_exception(request, exception):
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

        app.add_task(core.log_server_error(app, request, excstr))
    return response.text('something went wrong xd', status=500)

@app.get('/')
async def index(request):
    return render_template('index', 
        title='Modmail', 
        message='DM to contact mods!'
        )

@app.get('/login')
async def login(request):
    if request['session'].get('logged_in'):
        return response.redirect('http://'+app.url_for('dashboard.index'))

    data = {
        'client_id': config.GITHUB_CLIENT_ID,
        'scope': 'public_repo'
    }
    url = config.GITHUB_OAUTH_URL + urlencode(data)
    return response.redirect(url)

@app.get('/logout')
@core.login_required()
async def logout(request):
    request['session'].clear()
    return response.redirect(app.url_for('index'))

@app.get('/callback')
async def callback(request):
    """Github Callback"""
    try:    
        code = request.raw_args['code']
    except KeyError:
        # in the case of invalid callback like someoone played with the url
        return response.text('error: ' + request.raw_args['error'])                                    
    
    params = {
        'client_id': config.GITHUB_CLIENT_ID,
        'client_secret': config.GITHUB_SECRET,
        'code': code
    }

    resp = await app.session.post('https://github.com/login/oauth/access_token', params=params)
    query_string = parse_qs(await resp.text())
    github_access_token = query_string['access_token'][0]
    user = await core.Github.login(app, github_access_token)
    # app.loop.create_task(user.fork_repository())  # fork repo

    # gotta check if a token exists first

    document = await app.db.api.find_one({'user_id': user.id})
    exists = document is not None

    request['session']['logged_in'] = True

    if exists:
        request['session']['user'] = user
        request['session']['token'] = document['token']
        await app.db.api.update_one({'user_id': user.id}, {'$set': {'github_access_token': github_access_token}})
        return response.redirect('http://'+app.url_for('dashboard.index'))

    # Generate token
    token = secrets.token_hex(15)
    request['session']['user'] = user
    request['session']['token'] = token 

    await app.db.api.update_one(
        {'user_id': user.id}, 
        {'$set': {
                'username': user.username,
                'token': token,
                'iat': datetime.datetime.utcnow(), 
                'github_access_token': github_access_token,
                'metadata': {},
                'config': {},
                'logs': {},
                }
        }, upsert=True)

    return response.redirect('http://'+app.url_for('dashboard.index'))

# deprecated
@app.get('/logged-in')
async def logged_in(request):
    username = request.raw_args.get('username', 'there')
    with open('static/template.html') as f:
        html = f.read().format(
            title=f'Hey {username}!',
            message='You can now go back to discord and use the `<code>update</code>` command.'
        )
    return response.html(html)

# deprecated
@app.get('/already-logged-in')
async def already_logged_in(request):
    with open('static/template.html') as f:
        html = f.read().format(
            title='Already Logged In!',
            message='Please use the `<code>github logout</code>` command and logout first.'
        )
    return response.html(html)

# deprecated
@app.route('/modmail', host='api.kybr.tk', methods=['GET', 'POST'])
async def deprecated(request):
    '''Keep old url users working'''
    if request.method == 'POST':
        await app.session.post('https://api.modmail.tk/metadata', json=request.json)
        return response.json({'sucess': True})
    else:
        return response.redirect('https://api.modmail.tk/metadata')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
