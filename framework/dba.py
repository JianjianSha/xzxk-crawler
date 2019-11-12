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
    return sql

def insert_sql(tb_name, scheme):
    sql = "insert into %s (%s) values (%s getdate())" % (
        tb_name, 
        ', '.join([row[0] for row in scheme if row[0] != 'id']),
        "%s, " * (len(scheme) - 2))
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