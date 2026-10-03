import os
from concurrent.futures import ThreadPoolExecutor

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import tornado.ioloop
import tornado.web
import tornado.wsgi
from django.conf import settings
from django.core.wsgi import get_wsgi_application


def make_application():
    django_application = get_wsgi_application()
    wsgi_executor = ThreadPoolExecutor(
        max_workers=int(os.environ.get("WSGI_MAX_WORKERS", "8"))
    )
    django_container = tornado.wsgi.WSGIContainer(
        django_application,
        executor=wsgi_executor,
    )
    return tornado.web.Application(
        [
            (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": str(settings.BASE_DIR / "static")}),
            (r"/media/(.*)", tornado.web.StaticFileHandler, {"path": str(settings.MEDIA_ROOT)}),
            (r".*", tornado.web.FallbackHandler, {"fallback": django_container}),
        ]
    )


if __name__ == "__main__":
    application = make_application()
    application.listen(int(os.environ.get("PORT", "8000")), address=os.environ.get("HOST", "127.0.0.1"))
    tornado.ioloop.IOLoop.current().start()