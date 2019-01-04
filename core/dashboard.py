from sanic import Blueprint, response
from core import config, utils

dashboard = Blueprint('dashboard', host='dashboard.'+config.DOMAIN)

@dashboard.get('/')
@utils.login_required()
async def index(request):
    user = request['session']['user']
    user_id = user['id']
    username = user['username']
    data = await request.app.db.api.find_one({'user_id': user_id})
    token = data['token']
    has_starred = await utils.Github(request.app, data['github_access_token']).has_starred()

    return request.app.render_template('dashboard',
        title=f'Hey there!',
        message=f"<small>Token: <code id='token'>{token}</code></small>",
        has_starred=has_starred
    )