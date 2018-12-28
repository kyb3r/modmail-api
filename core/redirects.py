from sanic import Blueprint, response
from sanic.exceptions import abort
from core import config

rd = Blueprint('redirects')

REDIRECTS = {
    'github': 'https://github.com/kyb3r',
    'discord': 'https://discord.gg/etJNHCQ',
    'source': 'https://github.com/kyb3r/webserver'
}

@rd.get('/<path>')
async def redirects(request, path):
    endpoint = REDIRECTS.get(path)
    if not endpoint:
        abort(404)
    return response.redirect(endpoint)

@rd.get('/<repo>', host=f'repo.{config.DOMAIN}')
async def repo(request, repo):
    return response.redirect(f'https://github.com/kyb3r/{repo}')
