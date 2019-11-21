from framework.crawl.lst_dtl import MSCrawler
from datetime import datetime
from tasks import CFG_DIR
from framework.utils import js_wrapper
import random
from urllib import request, parse
import requests
import os
import time
import socket
import base64
import json
import base64
from framework.utils.env import IS_WINDOWS
from framework.dba import update_sql, insert_sql


if IS_WINDOWS:
    from Cryptodome.Cipher import DES3
    from Cryptodome.Util.Padding import unpad, pad
else:
    from Crypto.Cipher import DES3
    from Crypto.Util.Padding import unpad, pad

cfg_file = os.path.join(CFG_DIR, 'court_ws_cfg.yml')





def get_cookies_from_jsdom_1():
    '''integration mode'''
    import service.api as sapi
    ruishu = sapi.ruishu()
    return ruishu.GET()


def get_cookies_from_jsdom_2(url):
    resp = requests.get(url)
    return resp.text


def get_cookies_from_splash(splash_url):
    _params = {
        "har": "1",
        "html5_media": "false",
        "http_method": "GET",
        "png": 1,
        "render_all": False,
        "request_body": False,
        "resource_timeout": 0,
        "response_body": False,
        "viewport": "1024x768",
        "wait": 0.5,
        "images": 1,
        "html": 1,
        "expand": 1,
        "timeout": 90,
        "url": "http://wenshu.court.gov.cn/",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36",
        "lua_source": """function main(splash, args)
                          assert(splash:go(args.url))
                          assert(splash:wait(0.5))
                            splash.images_enabled = false
                          return {
                            cookie = splash:get_cookies()
                          }
                        end
                       """
    }
    res = requests.post(url=splash_url + '/execute', data=json.dumps(_params),
                        headers={"content-type": "application/json"})
    num = 1
    while res.status_code != 200 and num < 5:
        time.sleep(2)
        requests.post(url=splash_url + '/execute', data=json.dumps(_params),
                      headers={"content-type": "application/json"})
        num += 1
    if res.status_code == 200:
        cookies = {}
        res_json = res.json()
        for cookie in res_json['cookie'] if res_json else []:
            cookies[str(cookie['name'])] = str(cookie['value'])
        return cookies
    else:
        print('tried 5 times but all are failed')
        return None


def req_verify_token(size=24):
    '''generate a new _RequestVerificationToken'''
    arr = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 
           'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 
           'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 
           'u', 'v', 'w', 'x', 'y', 'z', 'A', 'B', 'C', 'D', 
           'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 
           'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 
           'Y', 'Z'];
    s = ''.join([str(round(random.random() * (len(arr)-1))) for _ in range(size)])
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
        self.splash_url = self.cfg.PROJECT.SPLASH.URL
        self.url = parse.urlparse(self.lst_url)
        self.session = requests.Session()
        if self.cfg.PROJECT.JSDOM.MODE == 'integration':
            self.jsdom_cookies_getter = get_cookies_from_jsdom_1
        elif self.cfg.PROJECT.JSDOM.MODE == 'webservice':
            self.jsdom_cookies_getter = get_cookies_from_jsdom_2

        scheme = self.cfg.DATABASES[self.db_name].TABLES[self.tb_name].FIELDS

        auto_gen_time_num = 0
        for field in scheme[::-1]:
            if field[0].endswith('time'):
                auto_gen_time_num += 1
            else:
                break
        self.record_length = len(scheme) - 1 - auto_gen_time_num
        

        self.cookies = {
            'SESSION': '',
            'HM4hUBT0dDOn80S': '',
            'HM4hUBT0dDOn80T': ''
        }
        self.lst_data = {
            'cfg': 'com.lawyee.judge.dc.parse.dto.SearchDataDsoDTO@queryDoc',
            'pageNum': 1,
            'sortFields': 's51:desc',       # s50: court cascade; s51: judge date
            'ciphertext': '',
            'pageSize': 5,
            'queryCondition': [],
            # if invalid, use `req_verify_token`
            '_RequestVerificationToken': req_verify_token() 
        }
        self.dtl_data = {
            'docId': '',
            'ciphertext': '',
            '__RequestVerificationToken': req_verify_token(),
            'cfg': 'com.lawyee.judge.dc.parse.dto.SearchDataDsoDTO@docInfoSearch'
        }

        self.headers = {
            'Host': 'wenshu.court.gov.cn',
    # 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'http://wenshu.court.gov.cn/website/wenshu/181217BMTKHNT2W0/index.html',
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
        self.session.headers = self.headers
        self._update_cookies()

    def _update_cookies(self):
        # update cookie via splash
        # self.cookies.update(get_cookies_from_splash(self.splash_url))

        # update cookie via jsdom
        cookies = self.jsdom_cookies_getter()
        if cookies.startswith('[empty]'):
            self.logger.error("jsdom(%s) cookies error" % self.cfg.PROJECT.JSDOM.MODE)
            print("jsdom(%s) cookies error" % self.cfg.PROJECT.JSDOM.MODE)
            raise RuntimeError
        d = {}
        for p in cookies.split(';'):
            k,v = p.strip().split('=')
            d[k] = v

        self.cookies.update(d)

    def _lst(self):
        '''
        return None: task failed
        return empty list: task successed, but no data returned
                            (maybe task completed or some web page with not data)
        return list: task successed, with data returned
        '''
        self.lst_data['pageNum'] = self.pg_index
        try:
            
            resp = self._request(self.lst_url, self.lst_data)
            if resp:
                if resp.status_code != 200:
                    self.logger.error("requesting %s with page index %d "
                                      "still fails" % (self.lst_url, self.pg_index))
                    return None
                
                self.cookies.update(resp.cookies.items())

                json_ = resp.json()
                if self.run_mode != 'release':
                    print(json_)
                    return None

                records = []
                if json_:
                    if 'result' in json_ and 'secretKey' in json_:
                        json_ = decipher(json_['result'], 
                                         json_['secretKey'], 
                                         time.strftime("%Y%m%d"))
                        if 'queryResult' in json_:
                            json_ = json_['queryResult']
                            if 'resultList' in json_:
                                list_ = json_['resultList']
                                for item_ in list_:
                                    record = self.json2tuple_ws(item_)
                                    if record is not None:
                                        if record[4]:
                                            records.append(record)
                                        else:
                                            self.logger.error("wenshu id missing: %r" % record)
                                if records:
                                    # save to database
                                    scheme = self.cfg.DATABASES[self.db_name].TABLES[self.tb_name].FIELDS
                                    try:
                                        self.dba[self.db_name].insert(
                                            insert_sql(self.tb_name, scheme), records
                                        )
                                    except Exception as e:
                                        self.logger.exception("%s (master: %d) data saving error. error: %s, "
                                                            "trying save once a time" % (self.cfg.PROJECT.NAME, 
                                                                                         self.inst_name,
                                                                                         str(e)))
                                        if 'duplicate key' in str(e):
                                            for r in records:
                                                try:
                                                    self.dba[self.db_name].insert(
                                                        insert_sql(self.tb_name, scheme), [r]
                                                    )
                                                except Exception as e:
                                                    self.logger.exception('%s (master: %d) faid to insert the record: %r' % 
                                                                          (self.cfg.PROJECT.NAME, self.inst_name, r))
                                                    print('%s (master: %d) faid to insert the record: %r' % 
                                                          (self.cfg.PROJECT.NAME, self.inst_name, r))

                return [r[4] for r in records if r[4]]  # doc id


        except Exception as e:
            self.logger.exception('failed when request %s with params [page: %d]. '
                                  'error: %s' % (self.lst_url, self.pg_index, str(e)))

        return None
        

    def json2tuple_ws(self, json_, doc_id=None):
        t = [0] * self.record_length

        province = ''
        city = ''
        county = ''
        try:
            for k in json_:
                if k == "1":
                    t[0] = json_[k]     # 案件名称
                elif k == "2":
                    t[1] = json_[k]     # 法院名称
                elif k == "3" or k == "36" or k == '37' or k == '38' or k == '39' or k == '40':
                    t[2] = json_[k]     # 审理法院
                elif k == '4':
                    t[3] = json_[k]     # 法院层级
                elif k == "5" or k == 'rowKey':
                    t[4] = json_[k]
                elif k == "6":
                    t[5] = json_[k]     # 文书类型
                elif k == "7":
                    t[6] = json_[k]     # 案号
                elif k == '8':
                    t[7] = json_[k]     # 案件类型
                elif k == '9' or k == '10':
                    t[8] = json_[k]     # 审判程序
                elif k == '11' or k == '12' or k == '13' or k == '14' or k == '15' or k == '16':
                    t[9] = json_[k]     # 案由
                elif k == '17':
                    t[10] = json_[k]    # 当事人
                elif k == '18':
                    t[11] = json_[k]    # 审判人员
                elif k == '19':
                    t[12] = json_[k]    # 律师
                elif k == '20':
                    t[13] = json_[k]    # 律所
                elif k == '21':
                    t[14] = json_[k]    # 全文
                elif k == '31' or k == 'cprq':
                    t[15] = json_[k]    # 裁判日期
                elif k == '32':
                    t[16] = json_[k]    # 不公开理由
                elif k == '33':
                    province = json_[k] # # 法院省份 
                elif k == '34':
                    city = json_[k]
                elif k == '35':
                    county = json_[k]
                elif k == '41':
                    t[18] = json_[k]    # 发布日期
                elif k == '42':
                    if t[15] == 0:
                        t[15] = json_[k]    # 裁判年份
                elif k == '43':
                    t[19] = json_[k]    # 公开类型
                elif k == '44':
                    t[20] = json_[k]    # 案例等级
                elif k == '46':
                    t[21] = json_[k]    # 结案方式
                elif k == '48':
                    t[22] = json_[k]    # 上网时间
                elif k == 'qwContent':
                    t[23] = json_[k]
            t[17] = '%s#%s#%s' % (province, city, county)
            if t[23] and isinstance(t[23], str):
                t[23] = str(base64.b64encode(t[23].encode('utf-8')), 'utf-8')
            if not t[4] and doc_id:
                t[4] = doc_id
            return tuple('%r'%i if i!= 0 else '' for i in t)
        except Exception as e:
            self.logger.exception('failed to parse the item in list page: %r' % json_)
        return None

    def _request(self, url, data):
        num = 1
        resp = None
        max_num = 5 if self.run_mode == 'release' else 2
        while num <= max_num:
            try:
                data['ciphertext'] = cipher()
                resp = self.session.post(url, 
                                         data=data, 
                                         cookies=self.cookies, 
                                         timeout=20)
                if resp.status_code != 200:
                    num += 1
                    print("status_code %d: preparing to update cookies" % resp.status_code)
                    # it may need to update cookie
                    self._update_cookies()
                else:
                    return resp
            except socket.timeout as e:
                num += 1
                print('socket timeout error. trying %d' % num)
            except Exception as e:
                print('failed to request %s, error: %s' % (url, str(e)))
        return resp

    def _dtl(self, url, args):
        '''
        return None: task failed
        return empty-tuple record: task successed, but no data needs returning
        return nonempty record: task successed, with data returned
        '''
        self.dtl_data['docId'] = args[0]
        resp = self._request(self.dtl_url, self.dtl_data)
        if resp:
            if resp.status_code != 200:
                self.logger.error("requesting %s with wenshu id %s "
                                  "still fails" % (self.dtl_url, args[0]))
                return None
            
            self.cookies.update(resp.cookies.items())

            json_ = resp.json()
            if self.run_mode != 'release':
                print(json_)
                return None
            
            if json_:
                if 'result' in json_ and 'secretKey' in json_:
                    json_ = decipher(json_['result'], 
                                     json_['secretKey'], 
                                     time.strftime("%Y%m%d"))
                    r = self.json2tuple_ws(json_, doc_id=args[0])
                    if r is None:
                        self.logger.error("failed to parse data: %r" % json_)
                        return None
                    else:
                        scheme = self.cfg.DATABASES[self.db_name].TABLES[self.tb_name].FIELDS
                        try:
                            self.dba[self.db_name].insert(
                                insert_sql(self.tb_name, scheme), [r])
                            return tuple()
                        except Exception as e:
                            if 'duplicate key' in str(e):
                                print('change action from insert to update')
                                try:
                                    self.dba[self.db_name].update(
                                        update_sql(self,tb_name, scheme, 
                                                self.cfg.DATABASES[self.db_name].TABLES[self.tb_name].INDICES, 
                                                r))
                                    return tuple()
                                except Exception as e:
                                    self.logger("failed to update wenshu (%s), error: %s"
                                                % (r[4], str(e)))
                                    print("failed to update wenshu %s" % r[4])
                            else:
                                print('failed to insert wenshu %s' % r[4])
                                self.logger("failed to insert wenshu (%s), error: %s"
                                            % (r[4], str(e)))
        return None

            

