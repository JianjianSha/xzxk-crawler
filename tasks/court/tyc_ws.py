from framework.crawl.lst_dtl import MSCrawler
from bs4 import BeautifulSoup
from urllib import request, parse
import requests
import time
import gzip
import os
from tasks import CFG_DIR


cfg_file = os.path.join(CFG_DIR, 'tyc_ws_cfg.yml')

class DCrawler(MSCrawler):
    def __init__(self, is_master):
        super(DCrawler, self).__init__(cfg_file, is_master)
        self.redis_date_key = self.redis_key_prefix+"date"

        self.date = self.redis.get(self.redis_date_key)
        self.activate_date_max = 0
        self.page_max = 0

        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.87 Safari/537.36',
            # 'Cookie': 'aliyungf_tc=AQAAAKC/2jyBKAIApGUYdEf/ytb4yw2Z; csrfToken=Q-47on8Cdd2FjgVDVe5VMzIB; TYCID=88599880262511ea8580070e2a6d5ecb; undefined=88599880262511ea8580070e2a6d5ecb; ssuid=1497467044; bannerFlag=undefined; Hm_lvt_e9ceb92f9ef221e0401c0d5b35aa93f1=1577175325; _ga=GA1.2.1259398021.1577175325; _gid=GA1.2.1089910488.1577175325; Hm_lpvt_e9ceb92f9ef221e0401c0d5b35aa93f1=1577175644'
        }
        if self.date is None:
            self.init_redis()
        else:
            self.date = str(self.date, 'utf-8')


    def init_redis(self):
        self.date = "20191201"
        self.redis.set(self.redis_date_key, self.date)

    def _lst(self):
        time.sleep(0.5)
        lst_url = self.lst_url % self.date
        if self.pg_index != 1:
            lst_url += "/p%d" % self.pg_index
        # print('url:', lst_url)
        req = request.Request(lst_url, headers=self.headers)
        us = []
        try:
            # r = requests.get(lst_url, headers=self.headers)
            r = request.urlopen(req)
            # print('code:', r.code)
            
            if r.code != 200:
                print('failed to request url', lst_url)
                us = None
            else:
            # print('cookie:')
            # print(r.cookies)
                page = r.read()
                page = gzip.decompress(page).decode('utf-8', errors='ignore')
            # page = r.text
            # print('content:', page[:1000])
                if not page:
                    print('failed decode the response content from url', lst_url)
                    us = None

            if us is not None:
                bs = BeautifulSoup(page, 'lxml')
                if self.activate_date_max == 0:
                    map_content = bs.find('div', class_='map-content')
                    if map_content is not None:
                        links = map_content.find_all('a', class_='btn -lg btn-primary-bd')
                        if links:
                            dates = [int(a.get_text()) for a in links]
                            self.activate_date_max = max(dates)
                    if self.activate_date_max == 0:
                        self.activate_date_max = 31
                    pages = bs.find('ul', class_='pagination')
                    if pages is not None:
                        pages = pages.find_all('li')
                        if pages:
                            pgs = []
                            for page in pages:
                                try:
                                    a = page.find('a').get_text().strip()
                                    if '<' in a or '>' in a:
                                        continue
                                    pgs.append(int(a.strip('.')))
                                except:
                                    pass
                            self.page_max = max(pgs)
                    if self.page_max == 0:
                        self.page_max = -1
                
                mt20 = bs.find('div', class_='mt20')
                if mt20 is not None:
                    items = mt20.find_all('div', class_='col-4')
                    if items:
                        print('prepare to parse item unid...')
                        for item in items:
                            u = item.find('a')
                            try:
                                u = u['href'].strip()
                                u = u.split('/')[-1]
                                us.append(u)
                            except:
                                pass
        except Exception as e:
            self.logger.error(str(e))
        
        # switch
        if self.pg_index == self.page_max:
            # set to first page
            self.redis.set(self.redis_pg_index, 1)
            date = int(self.date[-2:])
            month = int(self.date[-4:-2])
            if date == self.activate_date_max:
                # set to next month
                date = 1
                month -=1
                if month == 0:
                    month = 12
            else:   # set to next date
                date += 1
            self.date = '2019%2d%2d' % (month, date)
            self.redis.set(self.redis_date_key, self.date)
            if self.date == '20191201':
                raise 'crawling completed~!'    # crawling process is completed!!!

            self.page_max = 0
            self.activate_date_max = 0
        # print(us)
        return us
            
    def _dtl(self, url, args):
        time.sleep(0.3)
        req = request.Request(url, headers=self.headers)
        fields = self.cfg.DATABASES[self.db_name].TABLES[self.tb_name].FIELDS
        res = [0]*(len(fields)-1)
        
        if isinstance(args, str):
            res[2] = args
        elif isinstance(args, (tuple, list)):
            res[2] = args[0]
        try:
            # print('url', url)
            r = request.urlopen(req)
            if r.code != 200:
                print('\033[1;31mfailed to request url %s\033[0m' % url)
            else:
                page = r.read()
                page = gzip.decompress(page).decode(encoding='utf-8')
                # print(page[:1000])
                bs = BeautifulSoup(page, 'lxml')
                container = bs.find('div', class_='box-container -main')
                if container is not None:
                    title = container.find('h1', class_='title')
                    if title is not None:
                        res[0] = title.get_text().strip()
                    subhead = container.find('div', class_='subheading')
                    if subhead is not None:
                        spans = [s.get_text().strip() for s in subhead.find_all('span')]
                        for s in spans:
                            if s.startswith('2019'):
                                res[8] = s
                            else:
                                res[10] = s
                    banner = container.find_all('div', class_='lawsuit-banner')
                    for b in banner:
                        btitle = b.find('span', class_='banner-title')
                        kw = btitle.get_text() if btitle else None
                        items = b.find_all('a', class_='tag tag-lawsuit')
                        flatten_items = ','.join(item.get_text().strip() for item in items)
                        if '律所' in kw or '律师' in flatten_items:
                            res[6] = flatten_items
                        elif '公司' in kw or '公司' in flatten_items:
                            res[3] = flatten_items
                    main_content = container.find('div', class_='lawsuitcontent pb50 lawsuitcontentnew')
                    if main_content is not None:
                        # print(main_content)
                        divs = main_content.find_all('div')
                        txts = []
                        for i in range(len(divs)):
                            txt = divs[i].get_text().strip()
                            txts.append(txt)
                            if txt.endswith('法院'):
                                res[1] = txt
                            elif txt.endswith('书') and i < 3:
                                res[5] = txt
                            elif txt.endswith('号') and i < 4:
                                res[4] = txt
                            elif txt.endswith('日') and '月' in txt and '年' in txt and len(txt) < 13:
                                res[7] = txt
                        res[9] = '<br>'.join(txts)
                    else:
                        self.fprint('not find main content', 'red')
        except Exception as e:
            self.logger.error(str(e))

        if res[2] != 0:
            res = tuple(i if i != 0 else '' for i in res)
        else:
            res = tuple()
        return res
                    
                        
                            



        

