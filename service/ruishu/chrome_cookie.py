import sqlite3
import os
# from framework.utils.env import IS_WINDOWS
IS_WINDOWS = False


# Function to 
def decrypt_windows(encrypted_value):
    import win32crypt
    try:
        decrypted_value = win32crypt.CryptUnprotectData(encrypted_value.decode('utf-8'))
        return decrypted_value[1].decode('utf-8')
    except Exception as e:
        print('failed to decrypt chrome cookie on windows', str(e))
        return ''


def decrypt_unix(encrypted_value):
    from Crypto.Cipher import AES
    from Crypto.Protocol.KDF import PBKDF2
    # Trim off the 'v11' that Chrome/ium prepends
    encrypted_value = encrypted_value[3:]

    # Default values used by both Chrome and Chromium in OSX and Linux
    salt = b'saltysalt'
    iv = b' ' * 16
    length = 16

    # On Mac, replace MY_PASS with your password from Keychain
    # On Linux, replace MY_PASS with 'peanuts'
    # my_pass = MY_PASS
    # my_pass = my_pass.encode('utf8')
    my_pass = get_chrome_pass_unix()

    # 1003 on Mac, 1 on Linux
    iterations = 1

    key = PBKDF2(my_pass, salt, length, iterations)
    cipher = AES.new(key, AES.MODE_CBC, IV=iv)

    decrypted = cipher.decrypt(encrypted_value)
    x = decrypted
    return x[:-x[-1]].decode('utf8')        # get rid of padding


def get_chrome_pass_unix():
    import secretstorage
    bus = secretstorage.dbus_init()
    collection = secretstorage.get_default_collection(bus)
    for item in collection.get_all_items():
        if item.get_label() == 'Chrome Safe Storage':
            MY_PASS = item.get_secret()
            break
    else:
        raise Exception('Chrome password not found!')
    return MY_PASS


def get_cookie_from_local_db(host):
    if IS_WINDOWS:
        cookies_file = r'C:\Users\sjj\AppData\Local\Google\Chrome\User Data\Default\Cookies'
        decrypt = decrypt_windows
    else:
        cookies_file = '/home/jian/.config/google-chrome/Default/Cookies'
        decrypt = decrypt_unix

    d = {}
    if os.path.isfile(cookies_file):
        connection = sqlite3.connect(cookies_file)
        cursor = connection.cursor()
        sql = 'SELECT name, encrypted_value from cookies WHERE host_key = "%s"' % host
        cursor.execute(sql)
        cookies = cursor.fetchall()
        for cookie in cookies:
            d[cookie[0]] = decrypt(cookie[1])
        cursor.close()
        connection.close()
    return d


if __name__ == '__main__':
    # get_cookie_from_local_db("wenshu.court.gov.cn")
    if not IS_WINDOWS:
        val = b'v11\xb9\xba\xc6JcJ\xe51\xd2\xba\xf0)\xcf\x8fI\xec\xf8\n\xba\x90\xc1\'\xb7\xb6\xb0,P\xda\x8c\xba\x9b\x08O\xfe~{\x93\xc5\xea_\x87ja|8IrX\x1c\x18\xf3"\xca\x16+\xf7\xbdd\x1820\xfb\x06\x92\\<\x98t\xbd\xd6\x81gE\x9b(\xcf\xea\x8a\x16\xf2'
        decrypt(val)
    else:
        print('dont worry, be happy')