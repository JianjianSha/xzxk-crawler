"""
All data to be collected are in form of list-detail, so main
thread is used to request the list webpage, and some subthreads 
are created to request detail webpages.
"""

from ..config import load, dump
from ..dba import *
import os
from datetime import datetime
from queue import Queue, Full, Empty
import threading
from .proxy import user_agents, GetProxyIP_XICI, check_ip
from ..log import get_logger
import time
import redis


class Signal:
    def __init__(self):
        self.val = False

    def turn_on(self):
        self.val = True

    def turn_off(self):
        self.val = False

    def __bool__(self):
        return self.val

class ThreadCrawl(threading.Thread):
    def __init__(self, id_, proj_name, queue1, queue2, func, signal):
        super(ThreadCrawl, self).__init__()
        self.id_ = id_
        self.proj_name = proj_name
        self.queue1 = queue1
        self.queue2 = queue2
        self.signal = signal
        self.func = func
        self.args = None
        self.url = ''

    def state(self):
        return "thread %d of project %s is handling %s with arguments %r" % (
            self.id_, self.proj_name, self.url, self.args
        )

    def run(self):
        while True:
            
            record = None
            try:
                self.url, self.args = self.queue1.get(timeout=30)   # wait 30s
                record = self.func(self.url, self.args)
            except Empty as qe:
                if self.signal:
                    break
                continue
            except Exception as e:
                record = None

            try:
                self.queue2.put(record, timeout=300)
            except Full as e:
                logger = get_logger(self.proj_name)
                logger.exception(
                    "In thread %d of project %s, it's failed to put record %r into queue. "
                    "The request url is %s" % (self.id_, self.proj_name, record, self.url))

class LSTDTLCrawler:
    def __init__(self, cfg_file, cache_file):
        self.cache_file = cache_file
        self.cache = load(cache_file)
        self.cfg   = load(cfg_file)
        self.close_saving = False
        # self.pg_index = self.cache.pg_index
        self.lst_url = self.cfg.WEB.URL_0
        self.dtl_url = self.cfg.WEB.URL_1
        self.db_name, self.tb_name = self.cfg.WEB.TABLES[0].split('.')

        self.dba = {}
        
        # load special logger for this project
        self.logger = get_logger(
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                'log', '%s.log' % self.cfg.PROJECT.NAME)
        )
         
        self.queue1 = Queue(1000)
        self.queue2 = Queue(1000)
        self.signal = Signal()

        check = False
        for db_name in self.cfg.DATABASES:
            db = self.cfg.DATABASES[db_name]
            if db_name == 'CHECK':
                check = db
                continue
            self.dba[db_name] = DBA(db.HOST, 
                                    db.USER,
                                    db.PWD,
                                    db_name)
            for tb_name in db.TABLES:
                tb = db.TABLES[tb_name]
                if check and not self.dba[db_name].select(check_table_sql(tb_name))[0]:
                    self.dba[db_name].execute(
                        create_table_sql(tb_name, tb.FIELDS))

        # self.data, self.header can be set in derived class

    def run(self, args):
        self.threads = [
            ThreadCrawl(
                i, 
                self.cfg.PROJECT.NAME, 
                self.queue1, 
                self.queue2, 
                self._dtl,
                self.signal)
            for i in range(5)
        ]
        self.threads.append(threading.Thread(target=self._save))

        self._run(args)

    def _run(self, args):
        alive = args[0] if isinstance(args, tuple) else args

        for t in self.threads:
            t.start()
        while self._lst():
            # self.cache.pg_index = self.pg_index
            dump(self.cache_file, dict(self.cache))

            if self.cache.pg_index % 100 == 0:
                print('Synchronizing, and you can terminate the app manually right now')
                self._sync() # syncronize, provides the oppertunity for terminating app
                for t in self.threads[:-1]:
                    print(t.state())
            print('finished crawling %s at the page %d, %s' % (self.lst_url, self.cache.pg_index - 1, datetime.now()))
            if not alive.value:
                break

        self.signal.turn_on()
        print('prepare to exit...\n\nwait for closing crawl threads...')
        for t in self.threads[:-1]:
            t.join()
        self.close_saving = True
        print('wait for cloing saving-thread')
        self.threads[-1].join()

        if self._interrupt:
            print('interruption completed!')
        else:
            print('task completed~')            


    def _sync(self):
        while not self.queue1.empty():
            time.sleep(10)

        while not self.queue2.empty():
            time.sleep(10)


    def _lst(self):
        # request lst_url
        # construct dtl_url and put into self.queue1
        # increase pg_index

        raise NotImplemented



    def _dtl(self, url, args):
        raise NotImplemented

    def _save(self):
        """save to database"""
        records = []
        while True:
            try:
                if len(records) == 100:
                    scheme = self.cfg.DATABASES[self.db_name].TABLES[self.tb_name].FIELDS
                    self.dba[self.db_name].insert(
                        insert_sql(self.tb_name, scheme), records
                    )
                    records.clear()

                record = self.queue2.get(timeout=60)
                if record:
                    records.append(record)
            except Empty as qe:
                if self.close_saving:
                    break
            except Exception as e:
                self.logger.exception("data saving error. error: %s, records: %r" % (str(e), records))


        if records:
            try:
                scheme = self.cfg.DATABASES[self.db_name].TABLES[self.tb_name].FIELDS
                self.dba[self.db_name].insert(
                    insert_sql(self.tb_name, scheme), records
                )
            except Exception as e:
                self.logger.exception("data saving error. error: %s, records: %r" % (str(e), records))


class MSCrawler:
    '''
    Master-Slave Crawler.
    Any crawler instance can be master or slave, but can not be both of them
        at the same time. Only one master can exist ath the same time.
    '''
    def __init__(self, cfg_file, is_master):
        self.is_master = is_master
        self.cfg   = load(cfg_file)
        # self.cache = load(cache_file)
        self.inst_name = self.cfg.PROJECT.INST_NAME

        redis_url = self.cfg.PROJECT.REDIS.URL
        self.redis = redis.Redis.from_url(redis_url)
        self.redis_key_prefix = self.cfg.PROJECT.REDIS.KEY_PREFIX
        self.redis_key = self.redis_key_prefix + "dtl_args"
        self.redis_pg_index = self.redis_key_prefix + "pg_idx"
        self.run_mode = self.cfg.PROJECT.RUN_MODE

        # if this field is set to True, you must promise only one master instance
        #   mt most is running at the same time.
        #   (currently it do not support multi-master)
        self.reset_condition = False

        self.redis_arg_sep = self.cfg.PROJECT.REDIS.ARG_SEP
        self.lst_url = self.cfg.WEB.URL_0
        self.dtl_url = self.cfg.WEB.URL_1
        self.db_name, self.tb_name = self.cfg.WEB.TABLES[0].split('.')

        
        if is_master:
            self.duplicate_num = 0
            self.pg_index = self.redis.get(self.redis_key_prefix+"page:%d" % self.inst_name)
            if self.pg_index is None:
                self._get_page_atomic()
                if self.pg_index == 0:
                    self._get_page_atomic()
            else:
                self.pg_index = int(self.pg_index)
                if self.pg_index == 0:
                    self._get_page_atomic()
        else:
            self.arg = self.redis.get(self.redis_key_prefix+"arg:%d" % self.inst_name)
            if self.arg and not isinstance(self.arg, str):
                self.arg = str(self.arg, 'utf-8')
            
            

        self.dba = {}
        
        # load special logger for this project
        self.logger = get_logger(
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                'log', '%s.log' % self.cfg.PROJECT.NAME)
        )

        if self.cfg.PROJECT.PROXY_IP:
            self.user_agents = user_agents
            self.xici = GetProxyIP_XICI(self.redis)
            # self.invalid_ips = {}       # ips and their failure number
            self.ips = self.xici.load(type='ha') + self.xici.load(type='nt')
            self.ips = [tuple(ip.split(',')) for ip in self.ips]
            # print("get proxy ips: %s" % self.ips)
            # raise ValueError("useful proxy ips is too less: %s" % self.ips)

            # print("check proxy ips' validity...")
            # valid_ips = []
            # valid_ips2 = []
            # for ip in self.ips:
            #     check_ip(ip, valid_ips)
            #     time.sleep(0.5)
            #     if valid_ips:
            #         print(ip, " is useful")
            #         valid_ips2.append(ip)
            #     else:
            #         print(ip, " is usefless")
            #     valid_ips.clear()
            
            # if len(valid_ips2) < len(self.ips):
            #     print("please refresh proxy ips")
            #     self.logger.info("some proxy ips are useless, please refresh proxy ip pool")
            # self.ips = valid_ips2

            if len(self.ips) < 5:
                raise ValueError("useful proxy ips is too less: %s" % self.ips)


        check = False
        for db_name in self.cfg.DATABASES:
            db = self.cfg.DATABASES[db_name]
            if db_name == 'INITIALIZE':
                check = db
                continue
            self.dba[db_name] = DBA(db.HOST, 
                                    db.USER,
                                    db.PWD,
                                    db_name)
            if not (check and self.is_master):
                continue
            for tb_name in db.TABLES:
                tb = db.TABLES[tb_name]
                if not self.dba[db_name].select(check_table_sql(tb_name))[0]:
                    self.dba[db_name].execute(
                        create_table_sql(tb_name, tb.FIELDS, tb.INDICES))

    def run(self, args):
        self.alive = args[0] if isinstance(args, tuple) else args

        if self.is_master:
            
            self._master_prepare()
            while self._master_run() >= 0:
                info = '%s (master %d) spider finished scraping the ' \
                       'list-page %d at %s' % (self.cfg.PROJECT.NAME, self.inst_name,
                                               self.pg_index, datetime.now())
                print(info)
                # self.logger.info(info)

                if not self.alive.value:
                    print('interrupted by user...')
                    # exit by user interruption
                    break

                if self.reset_condition:
                    print("%s (master %d)preparing to reset conditions..."
                          % (self.cfg.PROJECT.NAME, self.inst_name))
                    self._reset_lst()
                else:
                    # get next page index
                    self._get_page_atomic()

            if not self.alive.value: 
                # only when quitted by user interruption, reset page index to 0.
                # any other cases all represent task failing, so it needs to 
                #   reserve the page index in cache, indicating the place 
                #   from where the rescraping will start next time, no matter 
                #   at this page index the scraping task successes(last list-page) 
                #   or fails(web page exception) actually.
                self.redis.set(self.redis_key_prefix+"page:%d" % self.inst_name, 0)
            self.logger.info('%s (master) spider: task completed~')
        else:
            records = []
            record = None           # save the temporary record
            while self._get_arg():
                record = self._slave_run()
                if record:
                    records.append(record)
                
                if record is None:      # task failed
                    break               

                self.arg = None
                print('%s (slave) is working now, %s' % (self.cfg.PROJECT.NAME, datetime.now()))
                if not self.alive.value:
                    print('exit soon since interrupted by user...')
                    break

                if len(records) == 10:
                    self._insert_batch(records)
                    records.clear()

            if records:
                self._insert_batch(records)
            # reset cache-key to None when task succeed, at any situation
            if record:
                self.redis.set(self.redis_key_prefix+"arg:%d" % self.inst_name, '')

    def _reset_lst(self):
        self.reset_condition = False
        self.duplicate_num = 0
        old_pg_index = self.pg_index
        self._get_page_atomic()
        if old_pg_index < self.pg_index:    # pg_index had not been reset this epoch
            # reset page index
            self.redis.set(self.redis_key_prefix+"page:%d" % self.inst_name, 1)
            self.redis.set(self.redis_pg_index, 1)
            self._get_page_atomic()

            
        
    def _master_prepare(self):
        pass

    def _get_page_atomic(self):
        # if there are many master, getting page index should
        #   be a exclusive process
        pipe = self.redis.pipeline(transaction=True)
        pipe.multi()
        pipe.incr(self.redis_pg_index)
        pg_index = pipe.execute()
        if pg_index:
            self.pg_index = int(pg_index[0]) - 1
            # cache up page index for this task instance
            if self.pg_index > 0:
                self.redis.set(self.redis_key_prefix+"page:%d" % self.inst_name, self.pg_index)
        else:
            print('failed to get page index atomicly, please check first')
            # raise RuntimeError

    def _get_arg(self):
        if self.arg:
            return True

        while self.arg is None:
            print('%s (slave: %d) is waiting for arg' % (self.cfg.PROJECT.NAME, self.inst_name))
            arg = self.redis.blpop(self.redis_key, 60)
            if arg and len(arg) == 2:
                self.arg = str(arg[1], encoding='utf-8')
            if not self.alive.value:
                print('interrupted by user, please wait for ending work...')
                break

        if self.arg:
            # if already got an arg, even though had been interrupted by user at the same time,
            #   it still go on to complete the detail task, and after this, close this app then.
            # no matter what happens, cache up it after an arg being released
            self.redis.set(self.redis_key_prefix+"arg:%d" % self.inst_name, self.arg)
            return True # get an arg

        return False    # interrupted by user


    def _slave_run(self):
        fail_number = 0
        max_num = 5 if self.run_mode == 'release' else 1
        while fail_number < max_num:

            args = self.arg.split(self.redis_arg_sep)
            if '%s' in self.dtl_url:
                url = self.dtl_url % (*args,)
            else:
                url = self.dtl_url
            record = self._dtl(url, args)
            if isinstance(record, tuple):
                # self.redis.watch(self.redis_key_prefix+arg)
                # val = self.redis.get(self.redis_key_prefix+arg) or 0
                # pipe = self.redis.pipeline(transaction=True)
                # pipe.multi()
                # pipe.set(self.redis_key_prefix+arg, int(val)+1)
                # pipe.execute()
                # self.redis.unwatch(self.redis_key_prefix+arg)


                # self.redis.incr(self.redis_key_prefix+arg)

                return record
            else:
                fail_number += 1
                print("failed once again, wait for 10s please...")
                time.sleep(30)

        print('%s (slave: %d) failed exceeding %d times, please check'
              ' log info and debug before continuing'
              % (self.cfg.PROJECT.NAME, self.inst_name, max_num))

        print('sleep 60s... \n(if interrupted this app, please wait until wakeup)')
        time.sleep(300)
        return tuple()
        
    def _insert_batch(self, records):
        if records:
            # save to database
            scheme = self.cfg.DATABASES[self.db_name].TABLES[self.tb_name].FIELDS
            sql = insert_sql(self.tb_name, scheme)
            try:
                
                self.dba[self.db_name].insert(
                    sql, records
                )
            except Exception as e:
                self.logger.exception("%s (slave) data saving error. error: %s,"
                                      % (self.cfg.PROJECT.NAME, str(e)))

                for r in records:
                    try:
                        self.dba[self.db_name].insert(
                            sql, [r]
                        )
                    except Exception as ee:
                        self.logger.exception("%s (slave %d) data saving error. error: %s,"
                                              "record: %r" 
                                              % (self.cfg.PROJECT.NAME, self.inst_name, str(e), r))

                


    def _master_run(self):
        '''
        return empty-list: task success, but no data returned
                            (such as task completed, or no data on some web page)
        return None: task failed
        return list of args(strings): task success, with data returned
        '''
        args = self._lst()

        if args is None or len(args)>0:
            self.duplicate_num = 0

        # print('args returned from list page: ', args)
        if args and args[0]:
            self.redis.rpush(self.redis_key, *args)
            return 1

        

        print('no data returned from %s at page %d' % (self.lst_url, self.pg_index))
        
        print('sleep 60s... \n(if interrupted this app, please wait until wakeup)')
        time.sleep(60)
        return 0
