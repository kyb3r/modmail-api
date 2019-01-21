from sanic import Blueprint, response


from core import config
from core.objects import LogEntry


domain = config.DOMAIN
host = f'logs.{domain}'

logs = Blueprint('logs', host=host)


@logs.get('/<user_id>/<key>')
async def getlogsfile(request, user_id, key):

    log = await request.app.db.logs.find_one({'_id': key})

    if not log:
        return response.text('Not found', status=404)

    log_entry = LogEntry(request.app, log)

    return log_entry.render_html()


@logs.get('/<key>')
async def getlogsfile_no_userid(request, key):

    log = await request.app.db.logs.find_one({'_id': key})

    if not log:
        return response.text('Not found', status=404)

    log_entry = LogEntry(request.app, log)

    return log_entry.render_html()

@logs.get('/raw/<key>')
async def getrawlogsfile(request, key):

    log = await request.app.db.logs.find_one({'_id': key})

    if not log:
        return response.text('Not found', status=404)

    log_entry = LogEntry(request.app, log)

    return log_entry.render_plain_text()

