from sanic import Blueprint, response
from core import config

domain = config.DOMAIN
host = None if config.DEV_MODE else f'logs.{domain}'
prefix = '/logs/' if config.DEV_MODE else '/'

logs = Blueprint('logs', host=host, url_prefix=prefix)

logs.get('/<guild_id>/<key>')
async def getlogsfile(request, guild_id, key):
    return response.json({'message': 'not implemented'})