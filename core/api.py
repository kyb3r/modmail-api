import secrets
import json
import os

from bson import json_util
from datetime import datetime
from sanic import Blueprint, response
from sanic_cors import CORS
from pymongo.errors import DuplicateKeyError
from pymongo import DeleteMany, ReturnDocument

from .utils import auth_required, config, validate_github_payload, log_server_update, log_server_stop, Github

from dhooks import Embed

domain = config.DOMAIN
host = f'api.{domain}'

api = Blueprint('api', host=host)

CORS(api, automatic_options=True)

def json_dumps(data):
    return json.dumps(data, indent=4)


@api.get('/')
async def index(request):
    endpoints = set()
    deprecated = set()

    for name, (route, handler) in request.app.router.routes_names.items():
        if name.startswith('api.') or name.startswith('modmail.') or route.startswith('api.'):
            route = route.replace('api.modmail.tk', '')
            if route in ['/', '/api/']:
                continue
            if route.startswith('api.kybr.tk'):
                deprecated.add(route)
            else:
                endpoints.add(route)

    resp = {'success': True, 'endpoints': list(endpoints), 'deprecated': list(deprecated)}

    return response.json(resp, dumps=json_dumps)


@api.post('/webhooks/github')
async def upgrade(request):
    if not validate_github_payload(request):
        return response.text('fuck off', 401)  # not sent by github
    request.app.loop.create_task(restart_later(request.app))
    return response.json({'success': True})


@api.get('/badges/instances.svg')
async def badges_instances(request):
    instances = await request.app.db.users.count_documents({})
    url = f"https://img.shields.io/badge/instances-{instances}-green.svg?style=for-the-badge"
    async with request.app.session.get(url) as resp:
        file = await resp.read()
    return response.raw(file, content_type='image/svg+xml', headers={'cache-control': 'no-cache'})


@api.get('/metadata')
async def get_modmail_info(request):
    app = request.app

    resp = await app.session.get('https://raw.githubusercontent.com/kyb3r/modmail/master/bot.py')
    text = await resp.text()

    version = text.splitlines()[24].split(' = ')[1].strip("'")

    data = {
        'latest_version': version,
        'instances': await app.db.users.count_documents({})
    }
    return response.json(data, dumps=json_dumps)

@api.get('/oembed.json')
async def oembed(request):
    return response.json({
        'provider_name': 'Effortlessly contact server moderators.',
        'author_name': 'Discord Modmail',
        'author_url': 'https://github.com/kyb3r/modmail'
    })

async def log_new_instance(request):
    data = request.json
    count = await request.app.db.users.count_documents({})

    em = Embed(color=0x36393F)
    em.add_field(name='Guild Name', value=data['guild_name'])
    em.add_field(name='Member Count', value=data['member_count'])
    em.add_field(name='Owner', value=f"<@{data.get('owner_id', 0)}>")
    selfhosted = data['selfhosted']
    em.set_footer(text=f"#{count} • {'selfhosted ' if selfhosted else ''}v{data['version']} • {data['bot_name']} ({data['bot_id']})", icon_url=data.get('avatar_url'))
    
    await request.app.new_instance_webhook.send(
        embed=em, 
        username='New Instance', 
        avatar_url='https://i.imgur.com/klWk4Si.png'
        )

@api.post('/metadata')
async def update_modmail_data(request):
    data = request.json

    valid_keys = (
        'guild_id', 'guild_name', 'member_count',
        'uptime', 'version', 'bot_id', 'bot_name',
        'latency', 'owner_name', 'owner_id', 'selfhosted',
        'last_updated', 'avatar_url'
    )

    if any(k not in valid_keys for k in data):
        return response.json({'message': 'invalid payload'}, 401)

    
    exists = await request.app.db.users.find_one({
        'guild_id': data['guild_id'],
        'bot_id': data['bot_id']
        })

    if exists is None:
        await log_new_instance(request)

    await request.app.db.users.update_one(
        {'bot_id': data['bot_id']},
        {'$set': data},
        upsert=True
    )

    return response.json({'success': 'true'})


async def restart_later(app):
    await log_server_update(app)
    await log_server_stop(app)
    await app.session.close()
    command = 'git pull && pm2 restart kyb3r.tk'
    os.system(f'echo {app.password}|sudo -S {command}')
