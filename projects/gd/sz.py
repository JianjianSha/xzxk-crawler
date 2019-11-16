from urllib import request, parse
from datetime import datetime
import os
from framework.crawl.lst_dtl import LSTDTLCrawler
from projects import CFG_DIR

cfg_file = os.path.join(CFG_DIR, 'gd_sz_cfg.yml')
cache_file = os.path.join(CFG_DIR, 'gd_sz_cfg.yml')


def _extract_dtl(r):
    content = r.get('XK_NR', '')
    establish_date = '1900-01-01'
    try:
        if content:
            pairs = [s.split(':') for s in content.split(';')]
            for pair in pairs:
                if len(pair) == 2:
                    if pair[0].endswith('日期'):
                        establish_date = pair[1]
    except Exception as e:
        pass

    return (r.get('RECORDID', 'def'), 
            r.get('XK_WSH', ''), 
            r.get('XK_XMMC',''), 
            r.get('XK_SPLB', ''),
            '',     # main_body type
            '',     # address
            r.get('XK_NR', ''),
            establish_date,     #
            r.get('XK_XDR', ''),
            r.get('XK_XDR_SHXYM', ''),  # credit code
            '',     # organization code
            r.get('XK_XDR_GSDJ', ''),
            r.get('XK_XDR_SWDJ', ''),   # tas register code
            r.get('XK_XDR_SFZ', ''),    # id card number
            r.get('XK_FR', ''),         # law person
            r.get('XK_JDRQ', ''), 
            r.get('XK_JZQ', ''),        # terminate data
            r.get('XK_XZJG', ''),
            r.get('DFBM', ''),          # district code
            r.get('XK_ZT', ''), 
            "", 
            r.get('ZZYXQX', ''))    # len == 22



class Crawler(LSTDTLCrawler):
    def __init__(self, cache_file, cfg_file):
        super(Crawler, self).__init__(cfg_file, cache_file)

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

    def _lst(self):
        self.data['pageIndex'] = self.pg_index
        d = parse.urlencode(self.data).encode('utf-8')
        req = request.Request(self.lst_url, data=d, headers=self.headers)
        try:
            page = request.urlopen(req, timeout=10).read()
            page = gzip.decompress(page).decode('utf-8', errors='ignore')
            if not page:
                return False

            json_ = json.loads(page)
            ls = json_['data'][0]['data'][0]['list']


            for l in ls:
                if l['RECORDID']:
                    url = self.dtl_url % l['RECORDID']
                    self.queue1.put((url,None))
                    continue
            
                self.logger.warn('failed to get detail for data: %r' % l)
            
        except Exception as e:
            self.logger.exception('failed to get list data at page: %d: %s' % (
                self.cache.pg_inde, str(e))
        self.cache.pg_index += 1
        return True

    def _dtl(self, url, args):
        req = request.Request(url, headers=xzxk_headers)
        try:
            page = request.urlopen(req, timeout=10).read()
            page = gzip.decompress(page).decode('utf-8', errors='ignore')
            if not page:
                return None
            json_ = json.loads(page)
            data_ = json_['data'][0]['data']
            return _extract_dtl(data_)
        except Exception as e:
            logger.exception('url: %s, error: %s' % (url, str(e))
            return None

