# database accessor

import pymssql
import functools
import collections.abc as container_abc


def check_table_sql(tb_name):
    sql = """if object_id(N'dbo.%s', N'U') is not null
                select 1
            else
                select 0
        """ % tb_name
    return sql
    

def create_table_sql(tb_name, scheme, indices=None):
    sql = "create table %s (%s);" % (
        tb_name, ', '.join([' '.join(low) for low in scheme]))
    if indices:
        for index in indices:
            sql += """\ncreate {0} nonclustered index {1}_idx on {2} 
                    ({1} asc);""".format(index[1], index[0], tb_name)
    print(sql)
    return sql

def select_sql(tb_name, where):
    '''where is a tuple'''
    sql = "select top 1 * from %s where %s='%s'" % (tb_name, where[0], where[1])
    return sql

def insert_sql(tb_name, scheme):
    auto_gen_time_num = 0
    for field in scheme[::-1]:
        if field[0].endswith('time'):
            auto_gen_time_num += 1
        else:
            break

    sql = "insert into %s (%s) values (%s %s)" % (
        tb_name, 
        ', '.join([row[0] for row in scheme if row[0] != 'id']),
        "%s, " * (len(scheme) - 1 - auto_gen_time_num),
        'getdate()' * auto_gen_time_num if auto_gen_time_num else '')
    return sql

def update_sql(tb_name, fields, indices, record):
    auto_gen_time_num = 0
    for field in fields[::-1]:
        if field[0].endswith('time'):
            auto_gen_time_num += 1
        else:
            break
    where = None
    for index in indices:
        if 'unique' in index:
            where = index[0]
            break
    assert where is not None

    idx = -1
    for i in range(len(record)):
        if where in fields[i+1]:
            idx = i
            break
    assert idx >= 0

    sql = None
    for k1, k2 in zip(
        fields[1:], 
        record+tuple(['getdate()']*auto_gen_time_num)):
        if not k2 or k1[0] == where:
            continue
        if sql:
            if k2 == 'getdate()':
                sql +=", %s=%s" % (k1[0], k2)
            else:
                sql +=", %s='%s'" % (k1[0], k2)
        else:
            sql = "%s='%s'" % (k1[0], k2)
    # sql = ', '.join(
    #     ["%s='%s'" % (k1[0], k2) for k1, k2 in zip(
    #      fields[1:], 
    #      record+tuple(['getdate()']*auto_gen_time_num))  
    #      if k2 and k1[0] != where])
    sql = "update %s set %s where %s='%s'" % (tb_name, sql, where, record[idx])
    return sql

class TempDBA:
    def __init__(self, dba, db_name):
        self.dba = dba
        self.db_name = db_name

    def __enter__(self):
        self.old_db_name = self.dba.database
        self.dba.database = self.db_name
    
    def __exit__(self, *args):
        self.dba.database = self.old_db_name
        return False


class DBA:
    def __init__(self, host, user, password, database=None):
        self.host = host
        self.user = user
        self.password = password
        self.database = database

    def set_database(database):
        self.database = database

    def select(self, sql):
        with pymssql.connect(host=self.host,
                             user=self.user,
                             password=self.password,
                             database=self.database) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                return cursor.fetchone()

    def select_many(self, sql):
        pass

    def execute(self, sql):
        with pymssql.connect(host=self.host,
                             user=self.user,
                             password=self.password,
                             database=self.database) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                conn.commit()

    def insert(self, sql, records):
        assert isinstance(records, (list, tuple))
        fst = records[0]
        if not isinstance(fst, tuple):
            records=[tuple(records)]

        with pymssql.connect(host=self.host,
                             user=self.user,
                             password=self.password,
                             database=self.database) as conn:
            with conn.cursor() as cursor:
                cursor.executemany(sql, records)
                conn.commit()

    def update(self, sql):
        with pymssql.connect(host=self.host,
                             user=self.user,
                             password=self.password,
                             database=self.database) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                conn.commit()