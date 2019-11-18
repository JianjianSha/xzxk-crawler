# credit  zhejiang  ningbo

from urllib import request, parse
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime
import os
from framework.crawl.lst_dtl import LSTDTLCrawler, MSCrawler
from projects import CFG_DIR

# cache_file = os.path.realpath(
#     os.path.join(os.path.dirname(__file__), '../../cfg', 'zj_nb_cache.yml'))

# cfg_file = os.path.realpath(
#     os.path.join(os.path.dirname(__file__), '../../cfg', 'zj_nb_cfg.yml'))
cfg_file = os.path.join(CFG_DIR, 'zj_nb_cfg.yml')
cache_file = os.path.join(CFG_DIR, 'zj_nb_cache.yml')



class CrawlerBase:
    def init(self):
        # all item names(and their orders) in the table of the detailed web page
        self.index = {
            '被执行人姓名/名称':0,
            '证件类型':1,
            '身份证号码/组织机构代码':2,
            '法定代表人或者负责人姓名':3,
            '执行法院':4,
            '省份':5,
            '执行依据文号':6,
            '立案时间':7,
            '案号':8,
            '做出执行依据单位':9,
            '生效法律文书确定的义务':10,
            '被执行人的履行情况':11,
            '失信被执行人行为具体情形':12,
            '已履行部分':13,
            '未履行部分':14,
            '发布时间':15
        }

        # data of post-request
        self.data = {
            'pageIndex':1,
            'LYID':'SXBZXR',
            'MC':'',
            'ZJHM':'',
            'yzm':''
        }
        # request headers
        self.headers = {
            'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            'Accept-Encoding':'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36',
            'Cookie': 'JSESSIONID=RTs_scIIT_MPXaYydO4RIjlqpIt7LeHJuPDiAHCMhE0rVb1pVhcV!1603537165; BIGipServerGGXY_pool=3576948595.20480.0000; Hm_lvt_961eea4eb5a95d403f857deddfba3baa=1573026646; Hm_lpvt_961eea4eb5a95d403f857deddfba3baa=1573026669'
        }

    def _parse_lst(self, req):
        resp = request.urlopen(req, timeout=20)
        if resp.code != 200:
            return None
        page = resp.read().decode('utf-8', errors='ignore')
        if not page:
            return None
        
        bs = BeautifulSoup(page, 'lxml')
        zx_list = bs.find('div', class_='zx_list')
        table = zx_list.find('table')
        tr_list = table.find_all('tr') if table else zx_list.find_all('tr')
        if tr_list:
            tr_list = tr_list[1:-1]   # remove header of table

        args = []
        for tr in tr_list:
            td_list = tr.find_all('td')
            if len(td_list) == 4:
                credit_body = td_list[0].get_text().strip()
                dishonest_item = td_list[1].get_text().strip()
                date = td_list[2].get_text().strip()
                a = td_list[3].find('a')
                onclick = a['onclick'] if a else None
                if onclick:
                    ptn = r"getDetailQG\('(.+)','(.+)'\)"
                    ms = re.findall(ptn, onclick)
                    if ms and len(ms[0]) == 2:
                        args.append(ms[0])
        return args

    def _parse_dtl(self, req):
        resp = request.urlopen(req, timeout=20)
        if resp.code != 200:
            print('resp http status is not 200. please refer to log for page content')
            self.logger.error('failed to get normal response from request %s, the '
                              'returned page content is\n %s' % 
                              (req.full_url, resp.read().decode('utf-8', errors='ignore')))
            return None
        # print('request url %s, and status code: %d' % (url, resp.code))
        page = resp.read().decode('utf-8', errors='ignore')

        if not page:
            return None

        bs = BeautifulSoup(page, 'lxml')
        ts_diva = bs.find('div', class_='ts_diva')
        table = ts_diva.find('table')
        tr_list = table.find_all('tr') if table else ts_diva.find_all('tr')

        record = [0]*len(self.index)
        record_failed = []
        for tr in tr_list:
            th = tr.find('th').get_text().strip()[:-1]
            td = tr.find('td').get_text().strip()
            if th in self.index:
                record[self.index[th]] = td.replace("'", "''")
            else:
                record_failed.append(th+':'+td)

        if record_failed:
            self.logger.error('Failed to parse data. Url: %s, unparsed data: %r' % (
                req.full_url, record_failed))
            return None
        else:
            # record.append(datetime.now().date())
            return [r if r else '' for r in record]




class Crawler(LSTDTLCrawler, CrawlerBase):
    def __init__(self):
        super(Crawler, self).__init__(cfg_file, cache_file)

        self.init()


    def _lst(self):
        self.data['pageIndex'] = self.cache.pg_index
        d = parse.urlencode(self.data).encode('utf-8')
        req = request.Request(self.lst_url, data=d, headers=self.headers)


        try:
            args = self._parse_lst(req)
            if args:
                for arg in args:
                    url = self.dtl_url % (*arg,)
                    self.queue1.put((url, arg))      # block

        except Exception as e:
            self.logger.exception('failed to get list data at page %s with '
                                  'pg_index %d, error: %s' % (self.cache.pg_index, 
                                                              str(e)))

        self.cache.pg_index += 1
        return True
            



    def _dtl(self, url, args):
        req = request.Request(url, headers=self.headers)
        
        try:
            record = self._parse_dtl(req)
            if record:
                record = tuple(record+args)

            return record
        except Exception as e:
            self.logger.exception('Error %s. Url: %s' % (str(e), url))
            return None


class DCrawler(MSCrawler, CrawlerBase):
    def __init__(self, is_master):
        super(DCrawler, self).__init__(cfg_file, is_master)

        self.init()

    def _lst(self):
        self.data['pageIndex'] = self.pg_index
        d = parse.urlencode(self.data).encode('utf-8')
        req = request.Request(self.lst_url, data=d, headers=self.headers)

        try:
            args = self._parse_lst(req)
            return args

        except Exception as e:
            self.logger.exception('failed to get list data at page %s with '
                                  'pg_index %d, error: %s' % (self.lst_url, 
                                                              self.pg_index, 
                                                              str(e)))
        return None


    def _dtl(self, url, args):
        req = request.Request(url, headers=self.headers)

        try:
            record = self._parse_dtl(req)
            if record:
                record = tuple(record+args)
            return record
        except Exception as e:
            self.logger.exception('%s (slave) Error %s. Url: %s' % (
                self.cfg.PROJECT.NAME, str(e), url))
            return None