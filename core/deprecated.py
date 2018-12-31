from urllib.parse import parse_qs
from pymongo.errors import DuplicateKeyError
from sanic import Blueprint, response

from utils.github import Github
from core import config

host = 'api.kybr.tk'
prefix = '/api/modmail'

deprecated = Blueprint('deprecated', host=host, url_prefix=prefix)


@deprecated.get('/github/userinfo')
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


@deprecated.get('/github/logout')
async def github_logout(request):
    user = await request.app.db.oauth.find_one({'type': 'github', '_id': request.token})
    if user is None:
        return response.json({'error': True, 'message': 'Unable to find user. Please go through OAuth.'}, status=403)
    else:
        await request.app.db.oauth.find_one_and_delete({'type': 'github', '_id': request.token})
        user = await Github.login(request.app, user['access_token'])
        return response.json({
            'error': False,
            'message': 'User logged out.',
            'user': {
                'username': user.username,
                'avatar_url': user.avatar_url,
                'url': user.url
            }
        })


@deprecated.get('/github/update-repository')
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


@deprecated.get('/github/callback')
async def modmail_github_callback(request):

    code = request.raw_args['code']
    
    params = {
        'client_id': 'e54e4ff0f234ee9f22aa',
        'client_secret': config.GITHUB_SECRET,
        'code': code
    }

    async with request.app.session.post('https://github.com/login/oauth/access_token', params=params) as resp:
        url = 'https://kybr.tk'
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
            return response.redirect(url + f'/logged-in?username={user.username}')
