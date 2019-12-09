from framework.crawl.lst_dtl import MSCrawler
from datetime import datetime
from tasks import CFG_DIR
from framework.utils import js_wrapper
import random
from urllib import request, parse
import requests
import os
import time
import random
import itertools
import socket
import base64
import gzip
import json
import base64
from framework.utils.env import IS_WINDOWS
from framework.dba import update_sql, insert_sql, select_sql


if IS_WINDOWS:
    from Cryptodome.Cipher import DES3
    from Cryptodome.Util.Padding import unpad, pad
else:
    from Crypto.Cipher import DES3
    from Crypto.Util.Padding import unpad, pad

cfg_file = os.path.join(CFG_DIR, 'court_ws_cfg.yml')








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
        if self.cfg.PROJECT.JSDOM.MODE == 'webservice':
            self.jsdom_url = self.cfg.PROJECT.JSDOM.URL

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
            # 'pageId': 'bb059ae562ac691f970afb54dc91e833',
            # 's8': '02',
            'cfg': 'com.lawyee.judge.dc.parse.dto.SearchDataDsoDTO@queryDoc',
            'pageNum': 1,
            'sortFields': 's50:desc',       # s50: court cascade; s51: judge date
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
            # 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.87 Safari/537.36',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36'
            # 'Cookie': 'HM4hUBT0dDOn80S=voCvUzhBCC64rRORu3DYJ355qXgnADLGi0Tzf2WbQ_VpG70.XcLZOYOF5nyu4j9k; '\
            #           'SESSION=33ed257b-d99f-4bb9-a75e-58b33f53a901; '\
            #           'HM4hUBT0dDOn80T=4jO19oukHhlssW720zCkKfp2MmSMbKm.0nH1Vic0K4dwUeSaPnh305zejNBfuXGPSA6Ai6IyP.'\
            #           'qhWJcdad1kFRJailzaByJX5KAj1TsnCoUt3jD5UiREhZBT2eIOrfMtsgLea3mko.8C2rX37jFB3OyHQJW6EINReInRo2.'\
            #           'VcB21vIWgxrb2T10VOOYxsv8Bna1uTV.8p6H1kruNF.m26Pb1rGzplNktyKJiR1Qg2FfVRKuR2ix7jWInOX1OZmgcmkSiAqGQHZs2VpQv5a.'\
            #           '3bivEWJf7fZPIBWbH5RNMzrEh6rk6nm1lRxb3QR8RF1TlydDMQBU74DpvrZF01da1j5BoSgLUQfuAMq3VMSrCI.yU_6qIJz2d6CgBx1FpTfoME8OQ'
        }

        if is_master:
            # self.sort_group = ['s51:desc', 's50:desc', 's52:desc']
            # filter_group = {'s4': [], 's8': [], 's6': [], 's11': []}
            # with open('tasks/court/full_text_dict.json', 'r') as f:
            #     ft_dict = json.load(f)
            #     fycj = ft_dict.get('fycj', None)
            #     ay = ft_dict.get('ay', None)
            #     wslx = ft_dict.get('wslx', None)
            #     ajlx = ft_dict.get('ajlx', None)
            #     if fycj:
            #         filter_group['s4'] = [i['code'] for i in fycj]
                
            #     if ay:
            #         filter_group['s11'] = [i['id'] for i in ay if i['parent'] == '#']
                
            #     if wslx:
            #         filter_group['s6'] = [i['code'] for i in wslx]
                
            #     if ajlx:
            #         filter_group['s8'] = [i['code'] for i in ajlx]

            # # do not use two kinds of filters at the same time,
            # #   but in the future, this rule may be broken
            # self.filter_group = list(itertools.chain(*[[(k, v) for v in filter_group[k]] for k in filter_group]))
            # self.sort_filter_idx = 0
            # self.lst_data['sortFields'] = self.sort_group[self.sort_filter_idx // len(self.filter_group)]
            # fk, fv = self.filter_group[self.sort_filter_idx % len(self.filter_group)]
            # self.lst_data[fk] = fv

            self.lst_data['sortFields'] = 's51:desc'

            
            

        self.session.headers = self.headers
        # self._update_cookies()                # 2019-12-09  wenshu website cancel RUISHU encryption


    def get_cookies_from_jsdom_1(self):
        '''integration mode'''
        import service.api as sapi
        ruishu = sapi.ruishu()
        return ruishu.GET()


    def get_cookies_from_jsdom_2(self):
        resp = requests.get(self.jsdom_url)
        return resp.text

    def _update_cookies(self):
        # update cookie via splash
        # self.cookies.update(get_cookies_from_splash(self.splash_url))

        # update cookie via jsdom
        cookies = self.get_cookies_from_jsdom_2() if self.cfg.PROJECT.JSDOM.MODE == 'webservice' else self.get_cookies_from_jsdom_1()
        num = 1
        while num < 3 and cookies.startswith('[empty]'): 
            cookies = self.get_cookies_from_jsdom_2() if self.cfg.PROJECT.JSDOM.MODE == 'webservice' else self.get_cookies_from_jsdom_1()
            num += 1
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
        time.sleep(2)
        self.lst_data['pageNum'] = self.pg_index
        try:
            
            resp = self._request(self.lst_url, self.lst_data)
            if resp:
                if resp.status_code != 200:
                    self.logger.error("requesting %s with page index %d "
                                      "still fails" % (self.lst_url, self.pg_index))
                    return None
                
                if resp.cookies:
                    print('update cookies: ', resp.cookies)
                    self.cookies.update(resp.cookies)

                try:
                    json_ = resp.json()
                except Exception as e:
                    print('failed to jsonize response: %s, page index %d' % (resp.text, self.pg_index))
                    if self.pg_index > 1000:
                        info_ = "page index is very large and no data is gotten, so reset query condition, " \
                            "current condition: (sort->%s,%s->%s) reset query condition"\
                            % (self.sort_group[self.sort_filter_idx // len(self.filter_group)],
                                *self.filter_group[self.sort_filter_idx % len(self.filter_group)])
                        print(info_)
                        self.reset_condition = True
                    return None
                if self.run_mode != 'release':
                    print(json_)
                    return None

                records = []
                new_records = []
                
                if json_:
                    if 'result' in json_ and 'secretKey' in json_:
                        json_ = decipher(json_['result'], 
                                         json_['secretKey'], 
                                         time.strftime("%Y%m%d"))

                        
                        # print("after deciphered: ", json_)
                        # print(type(json_))
                        json_ = json.loads(json_)
                        # print("after deserialized: ", json_)

                        
                        if 'queryResult' in json_:
                            json_ = json_['queryResult']
                            if 'resultList' in json_:
                                list_ = json_['resultList']
                                if len(list_) == 0:
                                    # on this web page, the list has no items(maybe its the last page)
                                    #   no no no, it is common the server returns empty list, so don't believe it
                                    # self.reset_condition = True
                                    info_ = "get json data, but queryResult is empty list, " \
                                            "current condition: (sort->%s,%s->%s) reset query condition"\
                                            % (self.sort_group[self.sort_filter_idx // len(self.filter_group)],
                                               *self.filter_group[self.sort_filter_idx % len(self.filter_group)])
                                    print(info_)
                                    self.logger.info(info_)
                                    return []
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
                                        new_records = records
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
                                                    new_records.append(r)
                                                except Exception as e:
                                                    self.logger.exception('%s (master: %d) failed to insert the record: %r' % 
                                                                          (self.cfg.PROJECT.NAME, self.inst_name, r))
                                                    print('%s (master: %d) failed to insert the record: %r' % 
                                                          (self.cfg.PROJECT.NAME, self.inst_name, (r[0],r[4])))

                time.sleep(5)
                if self.pg_index >= 1000 and len(records) == 0:
                    self.reset_condition = True
                    info_ = "page index is very large and no data is gotten, so reset query condition, " \
                            "current condition: (sort->%s,%s->%s) reset query condition"\
                            % (self.sort_group[self.sort_filter_idx // len(self.filter_group)],
                                *self.filter_group[self.sort_filter_idx % len(self.filter_group)])
                    print(info_)
                    self.logger.info(info_)
                return [r[4] for r in new_records if r[4]]  # doc id


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
                # in list_page, 1,2,7,9,10,26,31,43,44 are returned fields
                v = k   # be aware that `k` should not be compared with value starts with 's' below:
                if k[0] == 's':
                    k = k[1:]
                if k == "1":
                    t[0] = json_[v]     # 案件名称
                elif k == "2":
                    t[1] = json_[v]     # 法院名称
                elif k == "3" or k == "36" or k == '37' or k == '38' or k == '39' or k == '40':
                    t[2] = json_[v]     # 审理法院
                elif k == '4':
                    t[3] = json_[v]     # 法院层级
                elif k == "5" or k == 'rowkey':
                    t[4] = json_[v]
                elif k == "6":
                    t[5] = json_[v]     # 文书类型
                elif k == "7":
                    t[6] = json_[v]     # 案号
                elif k == '8':
                    t[7] = json_[v]     # 案件类型
                elif k == '9' or k == '10':
                    t[8] = json_[v]     # 审判程序
                elif k == '11' or k == '12' or k == '13' or k == '14' or k == '15' or k == '16':
                    t[9] = json_[v]     # 案由
                elif k == '17':
                    t[10] = json_[v]    # 当事人
                elif k == '18':
                    t[11] = json_[v]    # 审判人员
                elif k == '19':
                    t[12] = json_[v]    # 律师
                elif k == '20':
                    t[13] = json_[v]    # 律所
                elif k == '21':
                    t[14] = json_[v]    # 全文
                elif k == '31' or k == 'cprq':
                    t[15] = json_[v]    # 裁判日期
                elif k == '32':
                    t[16] = json_[v]    # 不公开理由
                elif k == '33':
                    province = json_[v] # # 法院省份 
                elif k == '34':
                    city = json_[v]
                elif k == '35':
                    county = json_[v]
                elif k == '41':
                    t[18] = json_[v]    # 发布日期
                elif k == '42':
                    if t[15] == 0:
                        t[15] = json_[v]    # 裁判年份
                elif k == '43':
                    t[19] = json_[v]    # 公开类型
                elif k == '44':
                    t[20] = json_[v]    # 案例等级
                elif k == '46':
                    t[21] = json_[v]    # 结案方式
                elif k == '48':
                    t[22] = json_[v]    # 上网时间
                elif k == 'qwContent':
                    t[23] = json_[v]
            t[17] = '%s#%s#%s' % (province, city, county)
            if t[23] and isinstance(t[23], str):
                try:
                    cnt = base64.b64encode(gzip.compress(t[23].encode('utf-8')))
                    t[23] = str(cnt, 'utf-8')
                    # t[23] = str(base64.b64encode(t[23].encode('utf-8')), 'utf-8')
                except Exception as ee:
                    self.logger.exception("compress & base encode error: ", str(e))
                    t[23] = t[23].replace("'", "''")
            if not t[4] and doc_id:
                t[4] = doc_id

            for i in range(len(t)):
                if isinstance(t[i], list) and t[i] and isinstance(t[i][0], str):
                    t[i] = '.|.'.join(t[i]).replace("'", "''")
                elif isinstance(t[i], str):
                    t[i] = t[i].replace("'", "''")
                else:
                    t[i] = ''
                
            return tuple(t)
        except Exception as e:
            self.logger.exception('failed to parse the item in list page: %r, error: %s' % (json_, str(e)))
        return None

    def _request(self, url, data):
        '''request implementation for lst and dtl'''
        num = 1
        resp = None
        max_num = 5 if self.run_mode == 'release' else 2
        while num <= max_num:
            try:
                if self.cfg.PROJECT.PROXY_IP and self.ips:
                    # self.session.headers['User-Agent'] = random.choice(self.user_agents)
                    ip = random.choice(self.ips)
                    # print('randomly choice ip: ', ip)
                    s = ip[2] + '://' + ip[0] + ':' + str(ip[1])
                    proxies = {'http': s, 'https': s}
                else:
                    proxies = None
                data['ciphertext'] = cipher()
                resp = self.session.post(url, 
                                         data=data, 
                                         cookies=self.cookies, 
                                         proxies=proxies,
                                         timeout=60)
                
                if resp.status_code == 202:
                    num += 1
                    print("status_code %d: preparing to update cookies" % resp.status_code)
                    time.sleep(30)
                elif resp.status_code != 200:
                    if resp.status_code >= 400 and self.cfg.PROJECT.PROXY_IP:
                        self.ips.remove(ip)
                        if len(self.ips) < 3:
                            print("proxy ip number is two little, "
                                    "please wait for more fresh proxy ips")
                            new_ips=self.xici.dynamic_get(total=100)
                            
                            self.ips = list(ew_ips.union(self.ips))
                            if len(self.ips) < 5:
                                raise ValueError("proxy ip error: cannot get more proxy ips")
                        print("use proxy ip (%r), status_code: %d, it recommends you switch proxy ip"
                              % (self.cfg.PROJECT.PROXY_IP, resp.status_code))
                    print("it will sleep 10s, and please analyse error in time, status code:", resp.status_code)
                    time.sleep(10)

                # it may need to update cookie
                # self._update_cookies()        # 2019-12-09  wenshu website cancel RUISHU encryption
                if resp.cookies:
                        print('update cookies: ', resp.cookies)
                        self.cookies.update(resp.cookies)
                if resp.status_code == 200:
                    return resp
            except socket.timeout as e:
                num += 1
                print('socket timeout error. trying %d' % num)
            except Exception as e:
                print('failed to request %s, error: %s' % (url, str(e)))
                if 'Caused by ConnectTimeoutError' in str(e) or 'Cannot connect to proxy' in str(e):
                    if self.cfg.PROJECT.PROXY_IP:
                        self.ips.remove(ip)
                        # if len(self.ips) < 2:
                        #     raise ValueError("useful proxy ips too less")
                time.sleep(1)
        return resp

    def _check_dtl(self, uid):
        '''check if details are already existed'''
        t = self.dba[self.db_name].select(select_sql(self.tb_name, ('uid', uid)))
        # in list_page, 1,2,7,9,10,26,31,43,44 are returned fields
        if t[15] == '' and t[17] == '' and t[24] == '' and t[12] == '' \
            and t[3] == '' and t[6] == '' and t[8] == '' and t[10] == '' \
                and t[11] == '':
            return False
        return True

    def _dtl(self, url, args):
        '''
        return None: task failed
        return empty-tuple record: task successed, but no data needs returning
        return nonempty record: task successed, with data returned
        '''
        if self._check_dtl(args[0]):
            print("uid %s already exists in database")
            return tuple()

        self.dtl_data['docId'] = args[0]
        resp = self._request(self.dtl_url, self.dtl_data)
        if resp:
            if resp.status_code != 200:
                self.logger.error("requesting %s with wenshu id %s "
                                  "still fails" % (self.dtl_url, args[0]))
                return None
            
            # print("response cookies: %s" % resp.cookies.items())
            if resp.cookies:
                print('update cookies: ', resp.cookies)
                self.cookies.update(resp.cookies)

            try:
                json_ = resp.json()
            except Exception as e:
                print("failed to jsonize response: %s, doc id %s" % (resp.text, args[0]))
                return None
            
            
            if json_:
                if 'result' in json_ and 'secretKey' in json_:
                    json_ = decipher(json_['result'], 
                                     json_['secretKey'], 
                                     time.strftime("%Y%m%d"))
                    json_ = json.loads(json_)
                    if self.run_mode != 'release':
                        print(json_)
                        return None
                    r = self.json2tuple_ws(json_, doc_id=args[0])
                    if r is None:
                        print("failed to parse json data, please check in log file, and here it go on...")
                    else:
                        tb = self.cfg.DATABASES[self.db_name].TABLES[self.tb_name]
                        scheme = tb.FIELDS
                        
                        try:
                            self.dba[self.db_name].insert(
                                insert_sql(self.tb_name, scheme), [r])
                        except Exception as ie:
                            if 'duplicate key' in str(ie):
                                print('change action from insert to update')
                                try:
                                    indices = tb.INDICES
                                    self.dba[self.db_name].update(
                                        update_sql(self.tb_name, scheme, indices, r))
                                except Exception as ue:
                                    self.logger.exception("failed to update wenshu, error: %s, and record is: %s"
                                                % (str(ue), r))
                                    print("failed to update wenshu %s" % r[4])
                            else:
                                print('failed to insert wenshu %s' % r[4])
                                self.logger.exception("failed to insert wenshu (%s), error: %s"
                                            % (r[4], str(ie)))
                else:
                    return None     # web error -> task failure
            else:
                return None         # web error -> task failure
        # only failed to scrape web page can be seen as task failed, other errors
        #   such convesion error or saving DB error is not truely failure, because we can
        #   recover data from log file later
        time.sleep(3)
        return tuple()      


    def _reset_lst(self):
        # return None
        super(DCrawler, self)._reset_lst()


        # self.sort_filter_idx += 1
        # self.lst_data['sortFields'] = self.sort_group[self.sort_filter_idx // len(self.filter_group)]
        # fk, fv = self.filter_group[self.sort_filter_idx % len(self.filter_group)]
        # self.lst_data[fk] = fv


    # filter: [{"key":"s38","value":"100"},{"key":"s11","value":"1"},{"key":"s4","value":"2"},{"key":"s42","value":"2019"},{"key":"s8","value":"02"}]
    # sort: s51->desc(裁判日期, cprq), s50->desc(法院层级,fycj), s52->desc( 审判程序,spcx)
    # filter: s38->(审理法院,slfy), s11->(案由,ay), s4->(法院层级, fycj), s42->(裁判年份), s8->(案件类型, ajlx), s6->(wslx)

    #     dataItemStr : {
		# "s1" : "案件名称",
		# "s2" : "法院名称",
		# "s3" : "审理法院",
		# "s4" : "法院层级",
		# "s5" : "文书ID",
		# "s6" : "文书类型",
		# "s7" : "案号",
		# "s8" : "案件类型",
		# "s9" : "审判程序",
		# "s10" : "审判程序",
		# "s11" : "案由",
		# "s12" : "案由",
		# "s13" : "案由",
		# "s14" : "案由",
		# "s15" : "案由",
		# "s16" : "案由",
		# "s17" : "当事人",
		# "s18" : "审判人员",
		# "s19" : "律师",
		# "s20" : "律所",
		# "s21" : "全文",
		# "s22" : "首部",   -- ignore start --
		# "s23" : "诉讼记录",
		# "s24" : "诉控辩",
		# "s25" : "事实",
		# "s26" : "理由",
		# "s27" : "判决结果",
		# "s28" : "尾部",
		# "s29" : "法律依据", 
		# "s30" : "",       -- ignore end --
		# "s31" : "裁判日期",
		# "s32" : "不公开理由",
		# "s33" : "法院省份",
		# "s34" : "法院地市",
		# "s35" : "法院区县",
		# "s36" : "审理法院",
		# "s37" : "审理法院",
		# "s38" : "审理法院",
		# "s39" : "审理法院",
		# "s40" : "审理法院",
		# "s41" : "发布日期",
		# "s42" : "裁判年份",
		# "s43" : "公开类型",
		# "s44" : "案例等级",
		# "s45" : "关键字",
		# "s46" : "结案方式",
		# "s47" : "法律依据",
		# "s48" : "上网时间",
		# "s49" : "案例等级排序",
		# "s50" : "法院层级排序",
		# "s51" : "裁判日期排序",
		# "s52" : "审判程序排序",
		# "s53" : "当事人段",
		# "s54" : "其他",
		# "cprqStart" : "裁判日期开始时间",
		# "cprqEnd" : "裁判日期结束时间",
		# "swsjStart" : "上网时间开始时间",
		# "swsjEnd" : "上网时间结束时间",
		# "flyj" : "法律依据",
		# "cprq" : "裁判日期"