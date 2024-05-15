import logging

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, Request
from uvicorn import Config, Server

logger = logging.getLogger(__name__)


async def health(request: Request):
    """
    Health check endpoint to ensure the service is up and running.
    Returns a JSON response with the health status.
    """
    logger.info("Heath check was hit")
    return JSONResponse({'status': 'healthy'})


web_app = Starlette(
    routes=[
        Route("/status", health, methods=["GET"]),
    ]
)


async def run_server_async():
    config = Config(web_app, host="0.0.0.0", port=8000)
    server = Server(config)
    await server.serve()
