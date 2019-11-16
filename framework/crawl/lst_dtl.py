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

        redis_url = self.cfg.PROJECT.REDIS.URL
        self.redis = redis.Redis.from_url(redis_url)
        self.redis_key_prefix = self.cfg.PROJECT.REDIS.KEY_PREFIX
        self.redis_key = self.redis_key_prefix + "dtl_args"
        self.redis_pg_index = self.redis_key_prefix + "pg_idx"


        self.redis_arg_sep = self.cfg.PROJECT.REDIS.ARG_SEP
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
                        create_table_sql(tb_name, tb.FIELDS))

    def run(self, args):
        alive = args[0] if isinstance(args, tuple) else args

        if self.is_master:
            self._master_prepare()
            while self._master_run():
                info = '%s (master) spider finished scraping the ' \
                       'list-page at %d' % (self.cfg.PROJECT.NAME, self.pg_index)
                print(info)
                # self.logger.info(info)

                if not alive.value:
                    break
            self.logger.info('%s (master) spider: task completed~')
        else:
            while True:
                self._slave_run()
                print('%s (slave) is working now, %s' % (self.cfg.PROJECT.NAME, datetime.now()))
                if not alive.value:
                    break

        
    def _master_prepare(self):
        self.pg_index = int(self.redis.get(self.redis_pg_index))
        if self.pg_index is None:
            self.pg_index = 1
            self.redis.set(self.redis_pg_index, self.pg_index)


    def _slave_run(self):
        records = []
        fail_number = 0
        while len(records) < 10:
            arg = self.redis.blpop(self.redis_key, 30)
            if arg:
                arg = str(arg[1], encoding='utf-8')
                args = arg.split(self.redis_arg_sep)
                url = self.dtl_url % (*args,)
                record = self._dtl(url, args)
                if record:
                    # self.redis.watch(self.redis_key_prefix+arg)
                    # val = self.redis.get(self.redis_key_prefix+arg) or 0
                    # pipe = self.redis.pipeline(transaction=True)
                    # pipe.multi()
                    # pipe.set(self.redis_key_prefix+arg, int(val)+1)
                    # pipe.execute()
                    # self.redis.unwatch(self.redis_key_prefix+arg)
                    self.redis.incr(self.redis_key_prefix+arg)

                    records.append(record)
                    fail_number = 0
                else:
                    fail_number += 1
            else:
                fail_number += 1

            if fail_number >= 10:
                print('%s (slave) failed exceeding 10 times, please check'
                      ' the log info and do some debugging before continuing to work')
                break
        
        if records:
            # save to database
            try:
                scheme = self.cfg.DATABASES[self.db_name].TABLES[self.tb_name].FIELDS
                self.dba[self.db_name].insert(
                    insert_sql(self.tb_name, scheme), records
                )
            except Exception as e:
                self.logger.exception("%s (slave) data saving error. error: %s,"
                                     "records: %r" % (self.cfg.PROJECT.NAME,
                                                      str(e), records))
                


    def _master_run(self):
        url_args = self._lst()

        if not url_args:
            return False

        self.redis.rpush(self.redis_key, 
                         *[self.redis_arg_sep.join(arg) for arg in url_args])

        self.pg_index += 1
        self.redis.set(self.redis_pg_index, self.pg_index)
        return True
