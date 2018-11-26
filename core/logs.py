import dhooks 
import socket

class Color:
    green = 0x2ecc71
    red = 0xe74c3c
    orange = 0xe67e22

def log_server_start(app):
    em = dhooks.Embed(color=Color.green)
    url = f'https://{app.cfg.domain}' if app.cfg.domain else None
    em.set_author('[INFO] Starting Worker', url=url)
    em.set_footer(f'Hostname: {socket.gethostname()} | Domain: {app.cfg.domain}')
    return app.webhook.send(embeds=em)

def log_server_stop(app):
    em = dhooks.Embed(color=Color.red)
    em.set_footer(f'Hostname: {socket.gethostname()} | Domain: {app.cfg.domain}')
    em.set_author('[INFO] Server Stopped')
    return app.webhook.send(embeds=em)

def log_server_update(app):
    em = dhooks.Embed(color=Color.orange)
    em.set_footer(f'Hostname: {socket.gethostname()} | Domain: {app.cfg.domain}')
    em.set_author('[INFO] Server updating and restarting.')
    return app.webhook.send(embeds=em)

def log_server_error(app, excstr):
    em = dhooks.Embed(color=Color.red)
    em.set_author('[ERROR] Exception occured on server')
    em.description = f'```py\n{excstr}```'
    em.set_footer(f'Hostname: {socket.gethostname()} | Domain: {app.cfg.domain}')
    return app.webhook.send(embeds=em)