from sanic import Blueprint, response

from .config import Config
from .utils import validate_github_payload

config = Config.from_json('config.json')
domain = config.domain

host = None if config.development else f'api.{domain}'
prefix = '/api' if config.development else None

api = Blueprint('api', host=host, url_prefix=prefix)

@api.post('/hooks/github')
async def upgrade(request):
    if not validate_github_payload(request):
        return response.text('fuck off', 401) # not sent by github
    request.app.loop.create_task(restart_later(request.app))
    return response.json({'success': True})

@api.get('/')
async def index(request):
    return response.json({'success': True, 'message': 'hello there, this api doesnt do anything lmao'})

async def restart_later(app):
    await core.log_server_update(app)
    await core.log_server_stop(app)
    await app.session.close()
    command = 'git pull && pm2 restart webserver'
    os.system(f'echo {app.password}|sudo -S {command}')