"""Privacy-minimized Tieba sign-in; adapted from LuoSue/TiebaSignIn-1 (MIT)."""
import hashlib
import http.client
import json
import os
import re
import ssl
import time
from urllib.parse import urlencode, urljoin, urlsplit

TBS = ('tieba.baidu.com', '/dc/common/tbs')
LIKE = ('c.tieba.baidu.com', '/c/f/forum/like')
SIGN = ('c.tieba.baidu.com', '/c/c/forum/sign')
ALLOWED = {TBS, LIKE, SIGN}
BASE = {'_client_type': '2', '_client_version': '9.7.8.0',
        '_phone_imei': '000000000000000', 'model': 'MI+5', 'net_type': '1'}

class Stop(Exception):
    def __init__(self, code='UNKNOWN', status=None):
        self.code = code
        self.status = status


SAFE_CODES = {'SECRET_MISSING', 'SECRET_FORMAT', 'AUTH_REJECTED', 'AUTH_SCHEMA',
              'AUTH_NETWORK', 'LIST_NETWORK', 'SIGN_NETWORK', 'AUTH_HTTP',
              'LIST_HTTP', 'SIGN_HTTP', 'AUTH_RESPONSE', 'LIST_RESPONSE',
              'SIGN_RESPONSE', 'LIST_REJECTED', 'LIST_SCHEMA', 'SIGN_REJECTED',
              'SIGN_UNAVAILABLE', 'UNKNOWN', 'AUTH_REDIRECT_SAME', 'AUTH_REDIRECT_SLASH',
              'AUTH_REDIRECT_OTHER_BAIDU', 'AUTH_REDIRECT_OTHER', 'AUTH_REDIRECT_MISSING'}

def request(endpoint, bduss, fields=None):
    if endpoint not in ALLOWED:
        raise Stop()
    stage = {TBS: 'AUTH', LIKE: 'LIST', SIGN: 'SIGN'}[endpoint]
    host, path = endpoint
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36', 'Cookie': 'BDUSS=' + bduss,
               'Accept': 'application/json'}
    body = None
    if fields is not None:
        fields = dict(fields, BDUSS=bduss)
        payload = ''.join(f'{k}={fields[k]}' for k in sorted(fields))
        fields['sign'] = hashlib.md5((payload + 'tiebaclient!!!').encode()).hexdigest().upper()
        body = urlencode(fields).encode()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    conn = http.client.HTTPSConnection(host, timeout=15, context=ssl.create_default_context())
    try:
        conn.request('POST' if body is not None else 'GET', path, body, headers)
        response = conn.getresponse()
        if endpoint == TBS and response.status in (301, 302, 303, 307, 308):
            location = response.getheader('Location')
            if not location:
                raise Stop('AUTH_REDIRECT_MISSING')
            target = urlsplit(urljoin('https://' + host + path, location))
            if target.scheme == 'https' and target.netloc == host:
                if target.path == path + '/' and not target.query and not target.fragment:
                    raise Stop('AUTH_REDIRECT_SLASH')
                if target.path == path:
                    raise Stop('AUTH_REDIRECT_SAME')
            if target.scheme == 'https' and target.hostname and (target.hostname == 'baidu.com' or target.hostname.endswith('.baidu.com')):
                raise Stop('AUTH_REDIRECT_OTHER_BAIDU')
            raise Stop('AUTH_REDIRECT_OTHER')
        if response.status != 200:
            raise Stop(stage + '_HTTP', response.status)
        raw = response.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise Stop(stage + '_RESPONSE')
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeError):
            raise Stop(stage + '_RESPONSE') from None
        if not isinstance(result, dict):
            raise Stop(stage + '_RESPONSE')
        return result
    except (OSError, http.client.HTTPException):
        raise Stop(stage + '_NETWORK') from None
    finally:
        conn.close()


def run(bduss):
    if not bduss:
        raise Stop('SECRET_MISSING')
    if not re.fullmatch(r'[A-Za-z0-9_~.%+/=\-]+', bduss):
        raise Stop('SECRET_FORMAT')
    auth = request(TBS, bduss)
    if str(auth.get('is_login')) == '0':
        raise Stop('AUTH_REJECTED')
    if str(auth.get('is_login')) != '1' or not isinstance(auth.get('tbs'), str) or not auth['tbs']:
        raise Stop('AUTH_SCHEMA')
    forums = {}
    for page in range(1, 51):
        result = request(LIKE, bduss, dict(BASE, _client_id='wappc_1534235498291_488',
            **{'from': '1008621y'}, page_no=str(page), page_size='200',
            timestamp=str(int(time.time())), vcode_tag='11'))
        if str(result.get('error_code', '0')) != '0':
            raise Stop('LIST_REJECTED')
        if not isinstance(result.get('forum_list'), dict):
            raise Stop('LIST_SCHEMA')
        for kind in ('non-gconforum', 'gconforum'):
            items = result['forum_list'].get(kind, [])
            if isinstance(items, dict):
                items = [items]
            if not isinstance(items, list):
                raise Stop('LIST_SCHEMA')
            for item in items:
                fid, name = str(item['id']), item['name']
                if not fid.isdigit() or not isinstance(name, str) or not name:
                    raise Stop('LIST_SCHEMA')
                forums[fid] = name
        more = str(result.get('has_more', '0'))
        if more == '0':
            break
        if more != '1':
            raise Stop('LIST_SCHEMA')
        time.sleep(2)
    else:
        raise Stop('LIST_SCHEMA')
    incomplete = False
    for fid, name in forums.items():
        time.sleep(2)
        result = request(SIGN, bduss, dict(BASE, fid=fid, kw=name, tbs=auth['tbs'],
            timestamp=str(int(time.time()))))
        status = str(result.get('error_code', ''))
        if status == '340006':
            incomplete = True
        elif status not in ('0', '160002'):
            raise Stop('SIGN_REJECTED')
    if incomplete:
        raise Stop('SIGN_UNAVAILABLE')


def main():
    try:
        run(os.environ.pop('BDUSS', ''))
    except Stop as exc:
        code = exc.code if exc.code in SAFE_CODES else 'UNKNOWN'
        if code in ('AUTH_HTTP', 'LIST_HTTP', 'SIGN_HTTP') and type(exc.status) is int and 100 <= exc.status <= 599:
            code += '_' + str(exc.status)
        print('Task incomplete. Diagnostic: ' + code)
        return 1
    except Exception:
        print('Task incomplete. Check your account manually.')
        return 1
    print('Task completed.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
