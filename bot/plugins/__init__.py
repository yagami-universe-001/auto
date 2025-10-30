import os
from aiohttp import web
from .route import routes

async def web_server():
    web_app = web.Application(client_max_size=30000000)
    asset_dir = os.path.join(os.getcwd(), "bot/assets")
    web_app.router.add_static('/assets/', asset_dir)
    web_app.add_routes(routes)
    return web_app