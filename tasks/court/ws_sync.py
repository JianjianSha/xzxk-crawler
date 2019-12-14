import gzip
import pymssql
import base64
from datetime import datetime

def select(sql):
    with pymssql.connect(host='192.168.2.199',
                         user='qzdata',
                         password='qzdata.admin',
                         database='QZCourt') as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchone()

def insert(sql, records):
    with pymssql.connect(host='192.168.2.199',
                         user='qzdata',
                         password='qzdata.admin',
                         database='QZCourt') as conn:
        with conn.cursor() as cursor:
            cursor.executemany(sql, records)
            conn.commit()

def selectmany(sql):
    with pymssql.connect(host='192.168.2.195',
                         user='qzdata',
                         password='qzdata.admin',
                         database='QZTemp') as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()


def transform(t):
    uid = t[5].upper()
    uid = '%s-%s-%s-%s-%s' % (uid[:8], uid[8:12], uid[12:16], uid[16:20], uid[12:])
    now = datetime.now().strftime('%Y-%m-%d')
    return uid, t[2], t[1], t[7], t[9], t[16], t[24], '#'*3, now, now

insert_sql = 'insert into JudgementDocCombine (jd_id, jd_courtHierarchy, jd_caseType, jd_docTitle, jd_caseNumber, jd_program, jd_docDate, jd_docContent, oc_code, createTime, updateTime, status) values (%s, %s,0,%s,%s,%s,%s,%s,%s,%s,%s,1)'

def sync_local_db():
    # offset of QZTemp.wenshu
    offset = 0
    ws_list = selectmany('select top 100 * from Wenshu where id > %d order by id' % offset)
    while len(ws_list)>0:
        ts = [transform(t) for t in ws_list]
        try:
            insert(insert_sql, ts)
        except Exception as e:
            if 'duplicate key' in str(e):
                for t in ts:
                    try:
                        insert(insert_sql, [t])
                    except Exception as ee:
                        print('failed to insert', t[0])

        offset = int( ws_list[0][0])
        ws_list = selectmany('select top 100 * from Wenshu where id > %d order by id' % offset)


def parse_ws_content():
    cnt = select('select top 1 jd_docContent from JudgementDocCombine where id=2195377')
    if cnt:
        # print("origin", cnt[0])
        cnt = base64.b64decode(cnt[0])
        cnt = gzip.decompress(cnt).decode('utf-8')
        print(cnt)
    else:
        print('no data')


if __name__ == '__main__':
    parse_ws_content()