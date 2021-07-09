import logging

from aiohttp import web
from logfmt_logger import getLogger

from .container import ApplicationContainer
from .infrastructure.api.setup import setup as api_setup
from .version import __version__


def init():
    """ Init application """
    # Init application container
    container = ApplicationContainer()

    # Override with env variables
    container.configuration.log_level.from_env("LOG_LEVEL", "INFO")
    # TODO: Add other configurations here

    # Setup logging
    str_level = container.configuration.log_level()
    numeric_level = getattr(logging, str_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError("Invalid log level: %s" % str_level)
    logger = getLogger(__name__, numeric_level)
    logger.info("Logging level is set to %s" % str_level.upper())

    # Init web app
    app: web.Application = web.Application()
    api_setup(app, container)
    app["container"] = container

    return app


async def on_startup(app: web.Application):
    """ Hooks for application startup """
    # container: ApplicationContainer = app["container"]
    # FIXME: add initialization hooks here
    pass


async def on_cleanup(app: web.Application):
    """ Define hook when application stop"""
    # container: ApplicationContainer = app["container"]
    # FIXME: add cleaning hooks here
    pass


def start():
    """ Start application """
    print(f"PHYSICS Global Continuum Placement version: {__version__}")
    app: web.Application = init()
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    web.run_app(app)
