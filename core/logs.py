from sanic import Blueprint, response
from sanic.exceptions import abort

from core import config


domain = config.DOMAIN
host = f'logs.{domain}'

logs = Blueprint('logs', host=host)

@logs.get('/<user_id>/<key>')
async def getlogsfile(request, user_id, key):
    try:
        auth_info = await request.app.db.api.find_one({'user_id': int(user_id)})
        if key in auth_info['logs']:
            return response.text(auth_info['logs'][key]['content'])
        else:
            return response.text('Not Found', status=404)
    except TypeError:
        # if auth_info is None or user_id isnt an integer
        return response.text('Not Found', status=404)
