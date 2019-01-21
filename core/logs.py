from sanic import Blueprint, response
import dateutil.parser
from datetime import datetime
from natural.date import duration
from markdown2 import markdown

from core import config


domain = config.DOMAIN
host = f'logs.{domain}'

logs = Blueprint('logs', host=host)


class LogEntry:
    def __init__(self, app, data):
        self.app = app
        self.key = data['key']
        self.open = data['open']
        self.created_at = dateutil.parser.parse(data['created_at'])
        self.closed_at = dateutil.parser.parse(data['closed_at']) if not self.open else None
        self.channel_id = int(data['channel_id'])
        self.guild_id = int(data['guild_id'])
        self.creator = User(data['creator'])
        self.recipient = User(data['recipient'])
        self.closer = User(data['closer']) if not self.open else None
        self.close_message = data.get('close_message')
        self.messages = [Message(m) for m in data['messages']]
    
    @property
    def system_avatar_url(self):
        return 'https://discordapp.com/assets/f78426a064bc9dd24847519259bc42af.png'
    
    @property
    def human_closed_at(self):
        return duration(self.closed_at)
    
    @property
    def message_groups(self):
        groups = []

        if not self.messages:
            return groups

        curr = MessageGroup(self.messages[0].author)
        
        for index, message in enumerate(self.messages):
            next_index = index + 1 if index + 1 < len(self.messages) else index
            next_message = self.messages[next_index]

            curr.messages.append(message)

            if message.is_different_from(next_message):
                groups.append(curr)
                curr = MessageGroup(next_message.author)
        
        groups.append(curr)
            
        return groups
            
    def render_html(self):
        for message in self.messages:
            message.format_html_content()

        return self.app.render_template('logbase', log_entry=self)
    
    def render_plain_text(self):
        return response.text(str(self))

    def __str__(self):
        out = f"Thread created at {self.created_at.strftime('%d %b %Y - %H:%M UTC')}\n"

        if self.creator == self.recipient:
            out += f'[R] {self.creator} ({self.creator.id}) created a modmail thread. \n'
        else:
            out += f'[M] {self.creator} created a thread with [R] {self.recipient} ({self.recipient.id})\n'
        
        out += '────────────────' * 3 + '\n'

        if self.messages:
            for index, message in enumerate(self.messages):
                next_index = index + 1 if index + 1 < len(self.messages) else index
                curr, next = message.author, self.messages[next_index].author 

                author = curr
                base = message.created_at.strftime('%d/%m %H:%M') + (' [M] ' if author.mod else ' [R] ')
                base += f'{author}: {message.content}\n'
                for attachment in message.attachments:
                    base += 'Attachment: ' + attachment + '\n'
                    
                out += base

                if curr != next:
                    out += '────────────────' * 2 + '\n'
                    current_author = author

        if not self.open:
            if self.messages:  # only add if at least 1 message was sent
                out += '────────────────' * 3 + '\n'            
            out += f'[M] {self.closer} ({self.closer.id}) closed the modmail thread. \n'
            out += f"Thread closed at {self.closed_at.strftime('%d %b %Y - %H:%M UTC')} \n"
                    
        return out


class User:
    def __init__(self, data):
        self.id = int(data.get('id'))
        self.name = data['name']
        self.discriminator = data['discriminator']
        self.avatar_url = data['avatar_url']
        self.mod = data['mod']
    
    @property 
    def default_avatar_url(self):
        return "https://cdn.discordapp.com/embed/avatars/{}.png".format(int(self.discriminator) % 5)
    
    def __str__(self):
        return f'{self.name}#{self.discriminator}'
    
    def __eq__(self, other):
        return self.id == other.id and self.mod is other.mod

class MessageGroup:
    def __init__(self, author):
        self.author = author
        self.messages = []
    
    @property
    def created_at(self):
        return self.messages[0].human_created_at

    @property
    def type(self):
        return self.messages[0].type

class Message:
    def __init__(self, data):
        self.id = int(data['message_id'])
        self.created_at = dateutil.parser.parse(data['timestamp'])
        self.human_created_at = duration(self.created_at, now=datetime.utcnow())
        self.content = data['content']
        self.attachments = data['attachments']
        self.author = User(data['author'])
        self.type = data.get('type', 'thread_message')
    
    def is_different_from(self, other):
        return (
            (other.created_at - self.created_at).total_seconds() > 60 
            or other.author != self.author or other.type != self.type
            )

    def replace(self, a, b):
        self.content = self.content.replace(a, b)
    
    def format_html_content(self):
        self.html_content = markdown(self.content)[3:-5]
        self.replace('\n', '<br>')
        self.replace("@everyone", "<span class=\"mention\">@everyone</span>")
        self.replace("@here", "<span class=\"mention\">@here</span>")


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

