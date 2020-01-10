import os
import time
from framework.utils.js_wrapper import js_ctx
from .ruishu.chrome_cookie import get_cookie_from_local_db

urls = (
    '/', 'index',
    '/ruishu', 'ruishu'
)


class index:
    def GET(self):
        g = '''
        Welcome to web service for enterprise's crawler arounding.
        We provide services as following:
        1. ruishu JS cracking   /ruishu
        2. CAPTCHA cracking     [to be released]
        '''
        return g

class ruishu:
    def __init__(self):
        self.version = 0

    def GET(self):
        d = get_cookie_from_local_db('wenshu.court.gov.cn')
        return ';'.join(['%s=%s' % (k,d[k]) for k in d])

    def GET_old(self):
        # if self.time is not None:
        #     if time.time() - self.time < 50.0:
        #         return self.cookies
        # self.time = self.cookies = None
        
        with js_ctx(
            os.path.join(os.path.dirname(__file__), 'ruishu/crack.js'),
            workspace=os.path.join(os.path.dirname(__file__), 'ruishu')
            # , os.path.join(os.path.dirname(__file__), 'ruishu/crack.js')
        ) as ctx:
            js_res = ctx.call("update_cookies")
            if js_res != 0:
                return "[empty]: calling js error"

            num = 1
            while num < 4:
                try:
                    with open(os.path.join(os.path.dirname(__file__), 
                                           'ruishu/cookies.txt'), 
                              'r', 
                              encoding='utf-8') as f:
                        cookies = f.read()  # HM4hUBT0dDOn80
                        if 'HM4hUBT0dDOn80S' in cookies or 'HM4hUBT0dDOn80T' in cookies:
                            # self.time = time.time()
                            # self.cookies = cookies
                            return cookies
                        else:
                            num += 1
                            time.sleep(1)
                except Exception as e:
                    return "[empty]: %d" % str(e)
            return "[empty]"

