from urllib.parse import parse_qs
from pymongo.errors import DuplicateKeyError
from sanic import Blueprint, response

from utils.github import Github
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


@modmail.get('/github/userinfo')
async def modmail_github_user(request):
    user = await request.app.db.oauth.find_one({'type': 'github', '_id': request.token})
    if user is None:
        return response.json({'error': True, 'message': 'Unable to find user. Please go through OAuth.'}, status=403)
    else:
        user = await Github.login(request.app, user['access_token'])
        return response.json({
            'error': False, 
            'message': 'User data retrieved.', 
            'user': {
                'username': user.username, 
                'avatar_url': user.avatar_url, 
                'url': user.url
            }
        })

@modmail.get('/github/logout')
async def github_logout(request):
    user = await request.app.db.oauth.find_one({'type': 'github', '_id': request.token})
    if user is None:
        return response.json({'error': True, 'message': 'Unable to find user. Please go through OAuth.'}, status=403)
    else:
        await request.app.db.oauth.find_one_and_delete({'type': 'github', '_id': request.token})
        return response.json({'error': False, 'message': 'User logged out.'})


@modmail.get('/github/update-repository')
async def modmail_github_check(request):
    user = await request.app.db.oauth.find_one({'type': 'github', '_id': request.token})
    if user is None:
        return response.json({'error': True, 'message': 'Unable to find user. Please go through OAuth.'}, status=403)
    else:
        user = await Github.login(request.app, user['access_token'])
        data = await user.update_repository()
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


@modmail.get('/logged-in')
async def logged_in(request):
    username = request.raw_args['username']
    with open('static/template.html') as f:
        html = f.read().format(
            title=f'Hey {username}!',
            message='You can now go back to discord and use the `<code>update</code>` command.'
        )
    return response.html(html)

@modmail.get('/already-logged-in')
async def already_logged_in(request):
    with open('static/template.html') as f:
        html = f.read().format(
            title='Already Logged In!',
            message='Please use the `<code>github logout</code>` command and logout first.'
        )
    return response.html(html)

@modmail.get('/github/callback')
async def modmail_github_callback(request):

    code = request.raw_args['code']
    params = {
        'client_id': 'e54e4ff0f234ee9f22aa',
        'client_secret': config.GITHUB_SECRET,
        'code': code
    }

    async with request.app.session.post('https://github.com/login/oauth/access_token', params=params) as resp:
        url = 'https://' + host + prefix
        data = parse_qs(await resp.text())
        try:
            await request.app.db.oauth.insert_one({
                'type': 'github', 
                '_id': request.raw_args['token'], 
                'access_token': data['access_token'][0]
                })
        except DuplicateKeyError:
            return response.redirect(url + '/already-logged-in')
        else:
            user = await Github.login(request.app, data['access_token'][0])
            return response.redirect(url + '/logged-in', username=user.name)
