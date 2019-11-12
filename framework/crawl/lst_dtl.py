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
            if self.signal:
                break
            record = None
            try:
                self.url, self.args = self.queue1.get(timeout=30)   # wait 30s
                record = self.func(self.url, self.args)
            except Empty as qe:
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
        self.queue2 = Queue(2000)
        self.signal = Signal()

        for db_name in self.cfg.DATABASES:
            db = self.cfg.DATABASES[db_name]
            self.dba[db_name] = DBA(db.HOST, 
                                    db.USER,
                                    db.PWD,
                                    db_name)
            for tb_name in db.TABLES:
                tb = db.TABLES[tb_name]
                if not self.dba[db_name].select(check_table_sql(tb_name))[0]:
                    self.dba[db_name].execute(
                        create_table_sql(tb_name, tb.FIELDS))

        # self.data, self.header can be set in derived class

    def run(self):
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

        self._run()

    def _run(self):
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

        self.signal.turn_on()
        for t in self.threads:
            t.join()
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
        count = 0
        while True:
            try:
                if len(records) == 100:
                    scheme = self.cfg.DATABASES[self.db_name].TABLES[self.tb_name].FIELDS
                    self.dba[self.db_name].insert(
                        insert_sql(self.tb_name, scheme), records
                    )
                    records.clear()

                record = self.queue2.get(timeout=120)
                records.append(record)
            except Empty as qe:
                if self.signal:
                    count += 1

                if count == 2:      # if failed to get item 2 times, quit the while-loop
                    break
            except Exception as e:
                self.logger.exception("data saving error. error: %s, records: %r" % (str(e), records))


        if records:
            scheme = self.cfg.DATABASES[self.db_name].TABLES[self.tb_name].FIELDS
            self.dba[self.db_name].insert(
                insert_sql(self.tb_name, scheme), records
            )


