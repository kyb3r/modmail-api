from sanic import Blueprint, response
from sanic.exceptions import abort
from core import config

rd = Blueprint('redirects')

REDIRECTS = {
    'github': 'https://github.com/kyb3r',
    'discord': 'https://discord.gg/etJNHCQ',
    'source': 'https://github.com/kyb3r/modmail-api',
    'changelog': 'https://github.com/kyb3r/modmail/blob/master/CHANGELOG.md'
}


@rd.get('/<path>')
async def redirects(request, path):
    endpoint = REDIRECTS.get(path)
    if not endpoint:
        abort(404)
    return response.redirect(endpoint)


@rd.get('/', host=f'github.{config.DOMAIN}')
async def repo(request, repo):
    return response.redirect('https://github.com/kyb3r/modmail')
