import azure.functions as func

# TODO: Take out try/catch once updated version of AsgiMiddleware is available for local installation
try:
    from azure.functions import AsgiMiddleware
except ImportError:
    from _future.azure.functions._http_asgi import AsgiMiddleware

from vgi_api import app


def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    return AsgiMiddleware(app).handle(req, context)
