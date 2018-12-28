import os

from sanic import Blueprint, response
import re

from core import config
from .utils import validate_github_payload
from .logs import log_server_stop, log_server_update, log_message

domain = config.DOMAIN

host = None if config.DEV_MODE else f'api.{domain}'
prefix = '/api/modmail' if config.DEV_MODE else '/modmail'

modmail = Blueprint('modmail', host=host, url_prefix=prefix)

@modmail.get('/')
async def get_modmail_info(request):
    app = request.app

    resp = await app.session.get('https://raw.githubusercontent.com/kyb3r/modmail/master/bot.py')
    text = await resp.text()
    await log_message(app, text[:2000])

    version = text.splitlines()[24].split(' = ')[1].strip("'")

    data = {
        'latest_version': version,
        'instances': await app.db.users.count_documents({})
    }
    return response.json(data)

@modmail.post('/')
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