from urllib.parse import parse_qs
import secrets
import json
import os

from datetime import datetime
from sanic import Blueprint, response
from sanic_cors import CORS
from pymongo.errors import DuplicateKeyError
from pymongo import ReturnDocument

from .utils import *

domain = config.DOMAIN
host = f'api.{domain}'

api = Blueprint('api', host=host)

CORS(api, automatic_options=True)

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

    return response.text(json.dumps(resp, indent=4))

@api.post('/webhooks/github')
async def upgrade(request):
    if not validate_github_payload(request):
        return response.text('fuck off', 401)  # not sent by github
    request.app.loop.create_task(restart_later(request.app))
    return response.json({'success': True})

@api.get('/logs/key')
@auth_required()
async def get_log_url(request, auth_info):
    # payload should have discord_uid, channel_id, guild_id
    user_id = auth_info['user_id']
    while True:
        key = secrets.token_hex(6)
        key_exists = await request.app.db.api.find_one({'logs.key': key})
        if not key_exists:
            log = await request.app.db.api.find_one_and_update(
                {'user_id': user_id},
                {'$set': {f"logs.{request.json['channel_id']}": {
                    'key': key,
                    'open': True,
                    'created_at': str(datetime.utcnow()),
                    'closed_at': None,
                    'user_id': user_id,
                    'channel_id': request.json['channel_id'],
                    'guild_id': request.json['guild_id'],
                    'creator': request.json['creator'],
                    'recipient': request.json['recipient'],
                    'closer': None,
                    'messages': [],
                }}}
            )
            return response.text(f'https://logs.modmail.tk/{user_id}/{key}')

@api.get('/logs/user/<user_id>')
@auth_required()
async def get_logs_user(request, auth_info, user_id):
    user_logs = []
    for i in auth_info['logs']:
        log = auth_info['logs'][i]
        if log['recipient']['id'] == user_id:
            user_logs.append(log)
    return response.json(user_logs)

@api.get('/logs/<channel_id>')
@auth_required()
async def get_log_data(request, auth_info, channel_id):
    """Get log data"""
    user_id = auth_info['user_id']
    if channel_id in auth_info['logs']:
        return auth_info['logs'][channel_id]
    else:
        return response.text('Not Found', status=404)
                
@api.post('/logs/<channel_id>')
@auth_required()
async def post_log(request, auth_info, channel_id):
    """Replaces the content"""
    user_id = auth_info['user_id']
    if channel_id in auth_info['logs']:
        log = await request.app.db.api.find_one_and_update(
            {'user_id': user_id},
            {'$set': {f'logs.{channel_id}.{i}': request.json[i] for i in request.json}},
            return_document=ReturnDocument.AFTER
        )
        return response.json(log['logs'][channel_id])
    else:
        return response.text('Not Found', status=404)

@api.patch('/logs/<channel_id>')
@auth_required()
async def patch_log_content(request, auth_info, channel_id):
    """Appends the content"""
    user_id = auth_info['user_id']

    if channel_id in auth_info['logs']:
        log = await request.app.db.api.find_one_and_update(
            {'user_id': user_id},
            {'$push': {f'logs.{channel_id}.messages': request.json['payload']}},
            return_document=ReturnDocument.AFTER
        )
        return response.json(log['logs'][channel_id])
    else:
        return response.text('Not Found', status=404)
                

@api.delete('/logs/<channel_id>')
@auth_required()
async def delete_log(request, auth_info, channel_id):
    """Delete log"""
    user_id = auth_info['user_id']
    if channel_id in auth_info['logs']:
        log = await request.app.db.api.find_one_and_update(
            {'user_id': user_id},
            {'$unset': {f'logs.{channel_id}'}},
            return_document=ReturnDocument.AFTER
        )
        return response.json(log['logs'][channel_id])
    else:
        return response.text('Not Found', status=404)

@api.get('/config')
@auth_required()
async def get_config(request, auth_info):
    '''Get config data'''
    return response.json(auth_info['config'])

@api.patch('/config')
@auth_required()
async def update_config(request, auth_info):
    user_id = auth_info['user_id']
    await request.app.db.api.update_one(
        {'user_id': user_id}, {'$set': request.json}
        )
    return response.json({'success': True})

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
    return response.json(data)


@api.post('/metadata')
async def update_modmail_data(request):
    data = request.json

    valid_keys = (
        'guild_id', 'guild_name', 'member_count',
        'uptime', 'version', 'bot_id', 'bot_name'
    )

    if any(k not in data for k in valid_keys):
        return response.json({'message': 'invalid payload'})

    await request.app.db.users.update_one(
        {'bot_id': data['bot_id']},
        {'$set': data},
        upsert=True
    )

    return response.json({'success': 'true'})

# GET - Get token
# PATCH - Regen token
# POST - Create token
@api.get('/token')
@auth_required()
async def get_token_info(request, auth_info):
    auth_info.pop('_id')
    return response.json(auth_info)

@api.patch('/token')
@auth_required()
async def regen_token(request, auth_info):
    new_token = secrets.token_hex(15)
    request['session']['token'] = new_token
    new_data = await request.app.db.api.find_one_and_update(
        {'user_id': auth_info['user_id']},
        {'$set': {'token': new_token}},
        return_document=ReturnDocument.AFTER
    )
    new_data.pop('_id')
    return response.json(new_data)

# @api.post('/token')
# @auth_required(admin=True) # ?? 
# # yeah
# # accept the metadata info in request.json
# # github stuff?yes # i'll put it aside for now 

@api.get('/github/userinfo')
@auth_required()
async def modmail_github_user(request, user):
    if user is None:
        return response.json({'error': True, 'message': 'Unable to find user. Please go through OAuth.'}, status=403)
    else:
        user = await Github.login(request.app, user['github_access_token'])
        return response.json({
            'error': False,
            'message': 'User data retrieved.',
            'user': {
                'username': user.username,
                'avatar_url': user.avatar_url,
                'url': user.url
            }
        })

@api.put('/star')
@auth_required()
async def star_repo(request, auth_info):
    await Github.login(request.app, auth_info['github_access_token']).star_repo()
    return response.text('', status=204)

async def restart_later(app):
    await log_server_update(app)
    await log_server_stop(app)
    await app.session.close()
    command = 'git pull && pipenv install && pm2 restart kyb3r.tk'
    os.system(f'echo {app.password}|sudo -S {command}')
