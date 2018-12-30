import os
import json

from sanic import Blueprint, response
from core import config

from .utils import validate_github_payload, log_server_stop, log_server_update


domain = config.DOMAIN
host = None if config.DEV_MODE else f'api.{domain}'
prefix = '/api' if config.DEV_MODE else None

api = Blueprint('api', host=host, url_prefix=prefix)

@api.get('/')
async def index(request):
    endpoints = set()

    for name, (route, handler) in request.app.router.routes_names.items():
        if name.startswith('api.') or name.startswith('modmail.') or route.startswith('api.'):
            route = route.replace('api.kybr.tk', '')
            if route in ['/', '/api/']:
                continue
            endpoints.add(route)

    resp = {'success': True, 'endpoints': list(endpoints)}

    return response.text(json.dumps(resp, indent=4))

@api.post('/hooks/github')
async def upgrade(request):
    if not validate_github_payload(request):
        return response.text('fuck off', 401)  # not sent by github
    request.app.loop.create_task(restart_later(request.app))
    return response.json({'success': True})


async def restart_later(app):
    await log_server_update(app)
    await log_server_stop(app)
    await app.session.close()
    command = 'git pull && pm2 restart webserver'
    os.system(f'echo {app.password}|sudo -S {command}')
