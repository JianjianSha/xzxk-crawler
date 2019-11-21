import web
from service.api import *


if __name__ == '__main__':
    app = web.application(urls, globals())
    app.run()
