import hmac
import hashlib
import dhooks
import socket
import os
import inspect
from functools import wraps

from core import config
from sanic.exceptions import abort
from sanic import response



def auth_required():
    
    unauthorized = response.json({'success': False, 'message': 'Invalid authorization.'}, status=401)

    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            if not request.token:
                return unauthorized
            document = await request.app.db.api.find_one({'token': request.token})
            if not document:
                return unauthorized
            return await func(request, document, *args, **kwargs)
        return wrapper
    return decorator

def login_required():
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            if not request['session'].get('logged_in'):
                return response.redirect(request.app.url_for('login'))
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

def get_stack_variable(name):
    stack = inspect.stack()
    try:
        for frames in stack:
            try:
                frame = frames[0]
                current_locals = frame.f_locals
                if name in current_locals:
                    return current_locals[name]
            finally:
                del frame
    finally:
        del stack

class Color:
    green = 0x2ecc71
    red = 0xe74c3c
    orange = 0xe67e22

class Github:
    BASE = 'https://api.github.com'
    REPO = BASE + '/repos/kyb3r/modmail'
    head = REPO + '/git/refs/heads/master'
    merge_url = BASE + '/repos/{username}/modmail/merges'
    fork_url = REPO + '/forks'
    star_url = BASE + '/user/starred/kyb3r/modmail'

    def __init__(self, app, access_token=None, username=None):
        self.app = app
        self.session = app.session
        self.access_token = access_token
        self.username = username
        self.id = None
        self.avatar_url = None
        self.url = None
        self.headers = None
        if self.access_token:
            self.headers = {'Authorization': 'token ' + str(access_token)}

    async def update_repository(self, sha=None):
        if sha is None:
            resp = await self.request(self.head)
            sha = resp['object']['sha']

        payload = {
            'base': 'master',
            'head': sha,
            'commit_message': 'Updating bot'
        }

        merge_url = self.merge_url.format(username=self.username)

        resp = await self.request(merge_url, method='POST', payload=payload)
        if isinstance(resp, dict):
            return resp

    async def fork_repository(self):
        await self.request(self.fork_url, method='POST')
    
    async def has_starred(self):
        resp = await self.request(self.star_url, return_response=True)
        return resp.status == 204

    async def star_repository(self):
        await self.request(self.star_url, method='PUT', headers={'Content-Length':  '0'})

    async def request(self, url, method='GET', payload=None, headers={}, return_response=False):
        headers.update(self.headers)
        async with self.session.request(method, url, headers=headers, json=payload) as resp:
            if return_response:
                return resp
            try:
                return await resp.json()
            except:
                return await resp.text()

    @classmethod
    async def login(cls, bot, access_token):
        self = cls(bot, access_token)
        resp = await self.request('https://api.github.com/user')
        self.username = resp['login']
        self.avatar_url = resp['avatar_url']
        self.url = resp['html_url']
        self.id = resp['id']
        self.raw_data = resp
        return self


def log_server_start(app):
    em = dhooks.Embed(color=Color.green)
    url = f'https://{config.DOMAIN}' if config.DOMAIN else None
    em.set_author('[INFO] Starting Worker', url=url)
    if url:
        cmd = r'git show -s HEAD~3..HEAD --format="[{}](https://github.com/kyb3r/webserver/commit/%H) %s"'
        cmd = cmd.format(r'\`%h\`') if os.name == 'posix' else cmd.format(r'`%h`')
        revision = '\n'.join(os.popen(cmd).read().strip().splitlines()[:3])
        em.add_field('Latest changes', revision, inline=False)
        em.add_field('Live at', url, inline=False)
        em.add_field('Github', 'https://github.com/kyb3r/webserver')

    em.set_footer(f'Hostname: {socket.gethostname()} | Domain: {config.DOMAIN}')
    return app.webhook.send(embeds=[em])

def log_server_stop(app):
    em = dhooks.Embed(color=Color.red)
    em.set_footer(f'Hostname: {socket.gethostname()} | Domain: {config.DOMAIN}')
    em.set_author('[INFO] Server Stopped')
    return app.webhook.send(embeds=[em])

def log_server_update(app):
    em = dhooks.Embed(color=Color.orange)
    em.set_footer(f'Hostname: {socket.gethostname()} | Domain: {config.DOMAIN}')
    em.set_author('[INFO] Server updating and restarting.')
    return app.webhook.send(embeds=[em])

def log_server_error(app, request, excstr):
    em = dhooks.Embed(color=Color.red)
    em.set_author('[ERROR] Exception occured on server}')
    em.description = f'{request.url}\n```py\n{excstr}```'
    em.set_footer(f'Hostname: {socket.gethostname()} | Domain: {app.cfg.DOMAIN}')
    return app.webhook.send(embeds=[em])

def log_message(app, message):
    em = dhooks.Embed(color=Color.orange)
    em.set_author('[INFO] Message')
    em.description = f'```\n{message}```'
    em.set_footer(f'Hostname: {socket.gethostname()} | Domain: {app.cfg.DOMAIN}')
    return app.webhook.send(embeds=[em])

def fbytes(s, encoding='utf-8', strings_only=False, errors='strict'):
    # Handle the common case first for performance reasons.
    if isinstance(s, bytes):
        return s
    if isinstance(s, memoryview):
        return bytes(s)
    else:
        return s.encode(encoding, errors)

def validate_github_payload(request):
    if not request.headers.get('X-Hub-Signature'):
        return False
    sha_name, signature = request.headers['X-Hub-Signature'].split('=')
    digester = hmac.new(
        fbytes(request.app.password),
        fbytes(request.body),
        hashlib.sha1
    )
    generated = fbytes(digester.hexdigest())
    return hmac.compare_digest(generated, fbytes(signature))
