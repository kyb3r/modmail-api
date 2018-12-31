from sanic import Blueprint, response
from core import config, utils

dashboard = Blueprint('dashboard', host='dashboard.'+config.DOMAIN)

@dashboard.get('/')
@utils.login_required()
async def index(request):
    user = request['session']['user']
    username = user['username']
    token = request['session']['token']
    return request.app.render_template('dashboard',
        title=f'Hey {username}',
        message=f"<small>Token: <code id='token'>{token}</code></small>"
    )