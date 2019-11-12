from utils.crawl import CrawlerBase
from utils.dba import insert_sql


class Crawler(CrawlerBase):
    def __init__(self, cache_file, cfg_file):
        super(Crawler, self).__init__(cache_file, cfg_file)

        assert 'nb' in self.cfg.PROJECTS
        nb = self.cfg.PROJECTS['nb']
        self.lst_url = nb.LST_URL
        self.dtl_url = nb.DTL_URL
        self.db_name, self.tb_name = nb.TABLE_NAME.split('.')

        # data of post-request
        self.data = {
            'action': 'getXZXKGSList',
            'Type': '',
            'keyword': '',
            'pageIndex': 1
        }
        # request headers
        self.headers = {
            'Accept':'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding':'gzip, deflate, br',
            'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36'
        }

    def _run(self):
        self.data['pageIndex'] = self.pg_index
        d = parse.urlencode(self.data).encode('utf-8')
        req = request.Request(self.lst_url, data=d, headers=self.headers)
        try:
            page = request.urlopen(req).read()
            page = gzip.decompress(page).decode('utf-8', errors='ignore')
            if not page:
                return False

            json_ = json.loads(page)
            ls = json_['data'][0]['data'][0]['list']


            records = []
            for l in ls:
                if l['RECORDID']:
                    record = self._dtl(l['RECORDID'])
                    if record:
                        records.append(record)
            
            if records:
                scheme = self.cfg.DATABASES[self.db_name].TABLES[self.tb_name].SCHEME
                self.dba[self.db_name].insert(
                    insert_sql(self.tb_name, scheme), records
                )
            
        except Exception as e:
            logger.exception(str(e))
        return True

    def _dtl(self, recordid):
        req = request.Request(self.dtl_url % recordid, headers=xzxk_headers)
        try:
            page = request.urlopen(req).read()
            page = gzip.decompress(page).decode('utf-8', errors='ignore')
            if not page:
                return None
            json_ = json.loads(page)
            data_ = json_['data'][0]['data']
            return data_
        except Exception as e:
            logger.exception(str(e))