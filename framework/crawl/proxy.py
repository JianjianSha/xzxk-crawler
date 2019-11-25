import requests
from bs4 import BeautifulSoup
import threading
import time
import os
from datetime import datetime
import redis


user_agents = [
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1"\
    "Mozilla/5.0 (X11; CrOS i686 2268.111.0) AppleWebKit/536.11 (KHTML, like Gecko) Chrome/20.0.1132.57 Safari/536.11",\
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1092.0 Safari/536.6",\
    "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.6 (KHTML, like Gecko) Chrome/20.0.1090.0 Safari/536.6",\
    "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/19.77.34.5 Safari/537.1",\
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.9 Safari/536.5",\
    "Mozilla/5.0 (Windows NT 6.0) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.36 Safari/536.5",\
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",\
    "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",\
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_0) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1063.0 Safari/536.3",\
    "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",\
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1062.0 Safari/536.3",\
    "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",\
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",\
    "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.1 Safari/536.3",\
    "Mozilla/5.0 (Windows NT 6.2) AppleWebKit/536.3 (KHTML, like Gecko) Chrome/19.0.1061.0 Safari/536.3",\
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",\
    "Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24"
]


 
# def dict2proxy(dic):
#     s = dic['type'] + '://' + dic['ip'] + ':' + str(dic['port'])
#     return {'http': s, 'https': s}


def check_ip(ip, ip_list):
    '''check ip's validity'''
    try:
        url = 'http://www.ipip.net'
        header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/64.0.3282.186 Safari/537.36'}
        s = ip[2] + '://' + ip[0] + ':' + str(ip[1])
        resp = requests.get(url, headers=header, proxies={'http':s, 'https':s}, timeout=10)
        if resp.status_code == 200:
            ip_list.append(ip)
        else:
            print("ip %r is invalid, resp status_code %d" 
                  % (ip, resp.status_code))
    except Exception as e:
        pass


class GetProxyIP_XICI:
    def __init__(self, *args):
        self.headers = {
    # 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.87 Safari/537.36',
        }
        self.pg_index = 1
        self.ha_url = 'http://www.xicidaili.com/nn/%d'     # get xicidaili's block of national high anonymous ips
        self.nt_url = 'http://www.xicidaili.com/nt/%d'      # get xicidaili's block of national transparent ips
        self.ips = []
        if args:
            self.redis = args[0]

    def run(self, batch=True):
        self._run(self.ha_url, batch=batch)
        if not batch:
            self._save(ha=self.ips)
        self._run(self.nt_url, max_page=2, batch=batch)
        if not batch:
            self._save(nt=self.ips)
            
    def _run(self, url, max_page=50, batch=True):
        num = 0         # count times for continuous request-failing
        self.pg_index = 1
        self.ips.clear()
        suffix = "ha" if "nn" in url else "nt"
        while self.pg_index < max_page:
            print("(%s) handling page index: %d" % (suffix, self.pg_index))
            url = url % self.pg_index
            resp = requests.get(url, headers=self.headers)
            resp.encoding = resp.apparent_encoding


            ips = []
            valid_ips = []
            if resp.status_code == 200:
                num = 0
                bs = BeautifulSoup(resp.text, 'lxml')
                items = bs.find_all('tr')[1:]       # skip table header
                
                for item in items:
                    tds = item.find_all('td')
                    ip, port, tape, time_ = tds[1].text, tds[2].text, tds[5].text.lower(), tds[9].text
                    if time_:
                        try:
                            time_ = datetime.strptime(time_, '%y-%m-%d %HH:%MM').time()
                            span_ = datetime.now() - time_
                            if span_.days > 365:    # if meets too old ip: stop getting ip
                                num = 100
                                break
                        except Exception as e:
                            pass
                    ips.append((ip, port, tape))

                print("number of ips in page %d: %d" % (self.pg_index, len(ips)))
            else:
                num += 1
                print("failed at page %d, total continuous failure number: %d" % (self.pg_index, num))

            

            

            threads = []
            for ip in ips:
                # because of GIL, do not worry about thread safty
                t = threading.Thread(target=check_ip, args=[ip, valid_ips])
                t.start()
                time.sleep(0.5)
                threads.append(t)

            if len(ips) < 10:
                time.sleep(5-0.5*len(ips))
            [t.join() for t in threads]
            
            if batch and valid_ips:
                
                self.redis.rpush("ip:"+suffix, 
                                 *['%s,%s,%s' % (*ip,) for ip in valid_ips])
            self.ips += valid_ips
            print("number of valid ips in page %d: %d" % (self.pg_index, len(valid_ips)))

            self.pg_index += 1
            if num > 10:
                break
        self.ips = list(set(self.ips))

    def dynamic_get(self, start_page=1):
        ha_ips = self._dynamic_get(self.ha_url, 1000, start_page)
        nt_ips = self._dynamic_get(self.nt_url, 100, start_page)
        return set(ha_ips+nt_ips)

    def _dynamic_get(self, url, total, start_page):
        self.pg_index = start_page
        ips = []

        while len(ips) < total:
            url = url % self.pg_index
            print("request %s for proxy ips" % url)
            resp = requests.get(url)
            resp.encoding = resp.apparent_encoding
            batch = []
            if resp.status_code == 200:
                bs = BeautifulSoup(resp.text, 'lxml')
                items = bs.find_all('tr')[1:]
                for item in items:
                    tds = item.find_all('td')
                    ip, port, tape = tds[1].text, tds[2].text, tds[5].text.lower()
                    batch.append((ip, port, tape))
            else:
                break

            threads = []
            for ip in batch:
                t = threading.Thread(target=check_ip, args=[ip, ips])
                t.start()
                time.sleep(0.5)
                threads.append(t)

            if len(batch) < 10:
                time.sleep(5-0.5*len(batch))
            [t.join() for t in threads]

        return ips


    def _save(self, **kwargs):
        self._write2redis(**kwargs)

    def _write2file(self, **kwargs):
        if kwargs:
            file_path = kwargs.get('file')
            if 'ha' in kwargs:
                ips = kwargs.get('ha')
                key = "ip_ha"
            elif 'nt' in kwargs:
                ips = kwargs.get('nt')
                key = "ip_nt"
            else:
                raise ValueError("must provide params: `ha` or `nt`")
            if not file_path:
                file_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                    'cfg/%s.txt' % key)

        else:
            raise ValueError("must provide params: `ha` or `nt`")

        if ips:
            with open(file_path, 'w') as f:
                f.writelines(['%s,%s,%s' % (*ip,) for ip in ips])

    def _write2redis(self, **kwargs):
        if kwargs:
            redis_cli = kwargs.get('redis', self.redis)
            if 'ha' in kwargs:
                ips = kwargs['ha']
                key = "ip:ha"
            elif 'nt' in kwargs:
                ips = kwargs['nt']
                key = 'ip:nt'
            else:
                raise ValueError("must provide param: `ha` or `nt`")
        else:
            raise ValueError("must provide param: `ha` or `nt`")
        if ips:
            redis_cli.delete(key)
            redis_cli.rpush(
                key,
                *['%s,%s,%s' % (*ip,) for ip in ips]
            )

    def load(self, **kwargs):
        r = self._loadfromredis(**kwargs)
        
        return r or []

    def _loadfromfile(self, **kwargs):
        if kwargs:
            file_path = kwargs.get('file')
            
            if 'type' in kwargs:
                key = 'ip_' + kwargs['type']
            else:
                raise ValueError("must provide param: `type`")

            if not file_path:
                file_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                    'cfg/%s.txt' % key)
            
        with open(file_path, 'r') as f:
            return f.readlines()

    def _loadfromredis(self, **kwargs):
        if kwargs:
            redis_cli = kwargs.get('redis', self.redis)
            if 'type' in kwargs:
                key = 'ip:' + kwargs['type']
            else:
                raise ValueError("must provide param: `type`")
        
        ips = redis_cli.lrange(key, 0, -1)
        return ips