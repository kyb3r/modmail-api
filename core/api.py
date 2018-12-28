import os

from urllib.parse import parse_qs
from sanic import Blueprint, response

from . import config
from .utils import validate_github_payload
from .logs import log_server_stop, log_server_update
from utils.github import Github


domain = config.DOMAIN

host = None if config.DEV_MODE else f'api.{domain}'
prefix = '/api' if config.DEV_MODE else None

api = Blueprint('api', host=host, url_prefix=prefix)


@api.post('/hooks/github')
async def upgrade(request):
    if not validate_github_payload(request):
        return response.text('fuck off', 401)  # not sent by github
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


@api.get('/modmail/heroku')
async def modmail_heroku_callback(request):
    code = request.raw_args['code']
    async with request.app.session.post(
        'https://id.heroku.com/oauth/token',
        data=f'grant_type=authorization_code&code={code}&client_secret={config.HEROKU_SERET}'
    ) as resp:
        data = await resp.json()
        await request.app.db.oauth.find_one_and_update(
            {'type': 'heroku', 'user_id': data['user_id']},
            {'$set': {'refresh_token': data['refresh_token'], 'access_token': data['access_token']}}
        )
    return response.text('Completed authentication. Please do the command again in discord.')


@api.get('/modmail/githubcheck/<userid>')
async def modmail_github_check(request, userid):
    userid = str(userid)
    user = await request.app.db.oauth.find_one({'type': 'github', 'user_id': userid})
    if user is None:
        return response.json({'error': True, 'message': 'Unable to find user. Please go through OAuth.'}, status=403)
    else:
        user, data = await update_modmail(request.app, user['access_token'])
        return response.json({
            'error': False, 
            'message': 'Updated modmail.', 
            'user': {
                'username': user.username, 
                'avatar_url': user.avatar_url, 
                'url': user.url
                }, 
            'data': data
        })


@api.get('/modmail/github')
async def modmail_github_callback(request):
    code = request.raw_args['code']
    async with request.app.session.post('https://github.com/login/oauth/access_token', params={
        'client_id': 'e54e4ff0f234ee9f22aa',
        'client_secret': config.GITHUB_SECRET,
        'code': code
    }) as resp:
        data = parse_qs(await resp.text())
        print(data)
        await request.app.db.oauth.find_one_and_update(
            {'type': 'github', 'user_id': request.raw_args['user_id']},
            {'$set': {'access_token': data['access_token'][0]}},
            upsert=True
        )
    await update_modmail(request.app, data['access_token'][0])
    return response.text('Completed update.')


async def update_modmail(app, access_token):
    user = await Github.login(app, access_token)
    data = await user.update_repository()
    return user, data


@api.get('/')
async def index(request):
    return response.json({'success': True, 'endpoints': ['/hooks/github', '/modmail']})


async def restart_later(app):
    await log_server_update(app)
    await log_server_stop(app)
    await app.session.close()
    command = 'git pull && pm2 restart webserver'
    os.system(f'echo {app.password}|sudo -S {command}')
