"""Точка входа Falcon WSGI-приложения."""
import falcon
from waitress import serve

from example.app.deps import bot
from example.app.resources import CallbackResource, CommandResource, StatusResource


def create_app() -> falcon.App:
    app = falcon.App()

    app.add_route("/command", CommandResource())
    app.add_route("/status", StatusResource())
    app.add_route("/notification/callback", CallbackResource())

    return app


application = create_app()


if __name__ == "__main__":
    bot.startup()
    try:
        serve(application, host="0.0.0.0", port=8000)
    finally:
        bot.shutdown()
