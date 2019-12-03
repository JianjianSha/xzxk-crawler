import gzip
import pymssql
import base64

def select(sql):
    with pymssql.connect(host='192.168.2.199',
                            user='qzdata',
                            password='qzdata.admin',
                            database='QZCourt') as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchone()


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