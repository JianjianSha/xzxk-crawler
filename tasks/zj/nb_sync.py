import yaml
from framework.easydict import EasyDict as edict
from framework.dba import DBA
from framework.log import get_logger
from datetime import datetime


class Sync:
    def __init__(self, cfg_file='cfg/zj_nb_sync_cfg.yml', 
                 cache_file='cfg/zj_nb_sync_cache.txt'):
        self.cache_file = cache_file
        with open(cache_file, 'r') as f:
            self.offset = int(f.readlines()[0].split(' ')[1])
        self.cfg = edict()
        self.num = 0
        with open(cfg_file, 'r', encoding='utf-8') as f:
            y = yaml.load(f)
            self.cfg.update(y)

        self.name = self.cfg.PROJECT.NAME
        self.batch = self.cfg.PROJECT.BATCH
        # self.logger = get_logger('log/zj.nb.sync.log')
        self.dba = {}
        for k in self.cfg.DATABASES:
            if k == 'INITIALIZE':
                continue
            p = self.cfg.DATABASES[k]
            self.dba[k] = DBA(p.HOST, p.USER, p.PWD, k)


    def _deduplicate(self):
        unids = self.dba['QZProperty'].select_many(
            'select top 100 unid from Executee group by unid having count(unid) > 1'
        )
        while len(unids) > 0:
            for unid in unids:
                ids = self.dba['QZProperty'].select_many(
                    'select id from Executee where unid = %s' % unid
                )
                
                ids = ','.join(ids[1:])

                self.dba['QZProperty'].execute(
                    'delete from Executeee where id in (%s)' % ids
                )
                
            print('finish %d' % len(unids))
            unids = self.dba['QZProperty'].select_many(
                'select top 100 unid from Executee group by unid having count(unid) > 1'
            )

    def run(self):
        self._deduplicate()
        # while self._get():
        #     self._transform()
        #     self._put()
        #     self.offset += self.num
        #     with open(self.cache_file, 'w') as f:
        #         f.writelines(["offset %d" % self.offset])
        #     print('offset %d at %s' % (self.offset, datetime.now()))
        #     break


    def _get(self):
        try:
            self.num = 0
            self.datas = self.dba['QZProperty'].select_many(
                'select top %d * from Executee where id > %d' 
                % (self.batch, self.offset))
            self.num = len(self.datas)
            return self.num > 0
        except Exception as e:
            print('error: getting data from QZProperty.Executee from offset %d'
                  % self.offset)
            raise e

    def _transform(self):
        datas = []
        ct = datetime.now().strftime('%Y-%m-%d')
        try:
            for d in self.datas:
                code = d[3].replace('-', '')
                if len(code) == 18:
                    code = code[8:17]
                elif len(code) > 20:
                    code = code[:20]
                data = -d[0], d[10], d[6], d[1], d[9], ct, ct, code
                datas.append(data)
        except Exception as e:
            print('error: failed to transform data')
            raise e
        self.datas = datas

    def _put(self):
        for data in self.datas:
            try:
                self.dba['QZCourt'].insert(
                    'insert into Zhixing (zx_id, zx_caseCode, zx_execCourtName, '
                    'zx_pname, zx_caseCreateTime, createTime, updateTime, status, '
                    'oc_code, zx_type) values (%s, %s, %s, %s, %s, %s, %s, 1, %s, 0)',
                    [data]
                )
            except Exception as e:
                print("error: failed to putting data(id->%s) into QZCourt.zhixing" % data[0])
                print(str(e))
                if 'duplicate key' not in str(e):
                    raise e
            
                
