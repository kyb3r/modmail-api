import os

from sanic import Blueprint, response
import re

from .config import Config
from .utils import validate_github_payload
from .logs import log_server_stop, log_server_update

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

@api.get('/modmail')
async def get_modmail_info(request):
    app = request.app

    resp = await app.session.get('https://raw.githubusercontent.com/kyb3r/modmail/master/bot.py')
    version = (await resp.text()).splitlines()[24].split(' = ')[1].strip("'")

    data = {
        'latest_version': version,
        'instances': await app.db.users.count_documents({})
    }
    return response.json(data)

@api.post('/modmail')
async def modmail(request):
    data = request.json
    valid_keys = (
        'guild_id', 'name', 'member_count', 
        'uptime', 'version', 'bot_id', 'bot_name'
        )

    if any(k not in data for k in valid_keys):
        return response.json({'message': 'invalid payload'})
    
    await request.app.db.users.update_one(
        {'guild_id': data['guild_id']}, 
        {'$set': data}, 
        upsert=True
        )

    return response.json({'success': 'true'})

@api.get('/')
async def index(request):
    return response.json({'success': True, 'endpoints': ['/hooks/github', '/modmail']})

async def restart_later(app):
    await log_server_update(app)
    await log_server_stop(app)
    await app.session.close()
    command = 'git pull && pm2 restart webserver'
    os.system(f'echo {app.password}|sudo -S {command}')