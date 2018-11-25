import os
from sanic import Sanic, response

app = Sanic(__name__)
dev_mode = bool(int(os.getenv('development')))
domain = None if dev_mode else os.getenv('domain')

def production_route(*args, **kwargs): # subdomains dont exist on localhost.
    def decorator(func):
        return func if dev_mode else app.route(*args, **kwargs)(func)
    return decorator

app.static('/static', './static')

@production_route('/')
async def wildcard(request):
    return response.text(f'Hello there, this subdomain doesnt do anything yet. ({request.host})')

@app.get('/', host=domain)
async def index(request):
    with open('static/index.html') as f:
        return response.html(f.read())

app.run(host='0.0.0.0', port=8000 if dev_mode else 80)