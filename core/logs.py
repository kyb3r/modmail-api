from sanic import Blueprint, response
from core import config

domain = config.DOMAIN
host = None if config.DEV_MODE else f'logs.{domain}'
prefix = '/logs' if config.DEV_MODE else None

logs = Blueprint('logs', host=host, url_prefix=prefix)
    
@logs.get('/')
async def index(request):
    return response.text('logs')

@logs.get('/<guild_id>/<key>')
async def getlogsfile(request, guild_id, key):
    return response.json({'message': 'not implemented'})