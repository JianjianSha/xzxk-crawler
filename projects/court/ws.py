from framework.crawl.lst_dtl import MSCrawler
from datetime import datetime
from projects import CFG_DIR
from framework.utils import js_wrapper
import random
from urllib import request, parse
import requests
import os
import base64
from framework.utils.env import IS_WINDOWS


if IS_WINDOWS:
    from Cryptodome.Cipher import DES3
    from Cryptodome.Util.Padding import unpad, pad
else:
    from Crypto.Cipher import DES3
    from Crypto.Util.Padding import unpad, pad

cfg_file = os.path.join(CFG_DIR, 'court_ws_cfg.yml')


def req_verify_token(size=24):
    '''generate a new _RequestVerificationToken'''
    arr = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 
           'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 
           'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 
           'u', 'v', 'w', 'x', 'y', 'z', 'A', 'B', 'C', 'D', 
           'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 
           'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 
           'Y', 'Z'];
    s = ''.join([round(random.random() * (len(arr)-1)) for _ in range(size)])
    return s


def cipher():
    with js_wrapper.js_ctx(
        os.path.join(os.path.dirname(__file__), 'cipher.js')) as ctx:
        return ctx.call('cipher')


def decipher(result, key, data):
    des3 = DES3.new(key=key.encode(), mode=DES3.MODE_CBC, iv=data.encode())
    decrypted_data = des3.decrypt(base64.b64decode(result))
    plain_text = unpad(decrypted_data, DES3.block_size).decode()
    return plain_text


class DCrawler(MSCrawler):
    def __init__(self, is_master):
        super(DCrawler, self).__init__(cfg_file, is_master)

        self.url = parse.urlparse(self.lst_url)
        self.session = requests.Session()
        self.cookies = {
            'SESSION': '',
            'HM4hUBT0dDOn80S': '',
            'HM4hUBT0dDOn80T': ''
        }
        self.data = {
            'cfg': 'com.lawyee.judge.dc.parse.dto.SearchDataDsoDTO@queryDoc',
            'pageNum': 1,
            'sortFields': 's51:desc',       # s50: court cascade; s51: judge date
            'ciphertext': '',
            'pageSize': 5,
            'queryCondition': [],
            # if invalid, use `req_verify_token`
            '_RequestVerificationToken': 'Qrb4DDp9xQDIEwPOrgpFlbgK' 
        }

        self.headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.87 Safari/537.36',
            # 'Cookie': 'HM4hUBT0dDOn80S=voCvUzhBCC64rRORu3DYJ355qXgnADLGi0Tzf2WbQ_VpG70.XcLZOYOF5nyu4j9k; '\
            #           'SESSION=33ed257b-d99f-4bb9-a75e-58b33f53a901; '\
            #           'HM4hUBT0dDOn80T=4jO19oukHhlssW720zCkKfp2MmSMbKm.0nH1Vic0K4dwUeSaPnh305zejNBfuXGPSA6Ai6IyP.'\
            #           'qhWJcdad1kFRJailzaByJX5KAj1TsnCoUt3jD5UiREhZBT2eIOrfMtsgLea3mko.8C2rX37jFB3OyHQJW6EINReInRo2.'\
            #           'VcB21vIWgxrb2T10VOOYxsv8Bna1uTV.8p6H1kruNF.m26Pb1rGzplNktyKJiR1Qg2FfVRKuR2ix7jWInOX1OZmgcmkSiAqGQHZs2VpQv5a.'\
            #           '3bivEWJf7fZPIBWbH5RNMzrEh6rk6nm1lRxb3QR8RF1TlydDMQBU74DpvrZF01da1j5BoSgLUQfuAMq3VMSrCI.yU_6qIJz2d6CgBx1FpTfoME8OQ'
        }

    def _update_headers(self, cookies):
        self.cookies.update(cookies)
        s = ''
        for k in self.cookies:
            s += '%s=%s; ' % (k, self.cookies[k])
        self.headers['Cookie'] = s[:-2]

    def _lst(self):
        self.data['pageNum'] = self.pg_index
        try:
            resp = self._requst_lst()
            # while not resp or resp.status_code != 200:
            #     if resp:
            #         print('(req cookie): ', self.cookies)
            #         print('(failed resp cookie): ', resp.cookies.items())
            #         self._update_headers(resp.cookies.items())
            #     resp = self._requst_lst()

            # if resp.cookies.items():
            #     self._update_headers(resp.cookies.items())
            if resp:
                self.cookies.update(resp.cookies.items())
            print('http status code: %s' % resp.status_code)

            print('cookies: ', resp.cookies.items())
            print('headers: ', resp.headers)
            
            page = resp.text
            print('(page): ', page)
        except Exception as e:
            self.logger.exception('failed when request %s with params [page: %d]. '
                                  'error: %s' % (self.lst_url, self.pg_index, str(e)))

        return None

    def _requst_lst(self):
        try:
            self.data['ciphertext'] = cipher()
            self.session.headers.update(self.headers)
            resp = self.session.post(self.lst_url, data=self.data, cookies=self.cookies, timeout=20)
            return resp
        except Exception as e:
            print('failed to request %s, error: %s' % (self.lst_url, str(e)))
        return None