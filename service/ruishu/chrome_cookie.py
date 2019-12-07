import sqlite3
import os
# from framework.utils.env import IS_WINDOWS
IS_WINDOWS = False

def get_cookie_from_local_db(host):
    if IS_WINDOWS:
        cookies_file = 'C:\Users\sjj\AppData\Local\Google\Chrome\User Data\Default\Cookies'
    else:
        cookies_file = '/home/jian/.config/google-chrome/Default/Cookies'

    if os.path.isfile(cookies_file):
        connection = sqlite3.connect(cookies_file)
        cursor = connection.cursor()
        sql = 'SELECT * from cookies WHERE host_key = "%s"' % host
        cursor.execute(sql)
        cookies = cursor.fetchall()
        for cookie in cookies:
            print(cookie, cookie[12].decode('ANSI'))
        cursor.close()
        connection.close()

if __name__ == '__main__':
    get_cookie_from_local_db("wenshu.court.gov.cn")