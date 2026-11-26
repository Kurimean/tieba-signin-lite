"""Privacy-minimized Tieba sign-in; adapted from LuoSue/TiebaSignIn-1 (MIT)."""
import hashlib
import http.client
import json
import os
import re
import ssl
import time
from urllib.parse import urlencode

TBS = ('tieba.baidu.com', '/dc/common/tbs')
LIKE = ('c.tieba.baidu.com', '/c/f/forum/like')
SIGN = ('c.tieba.baidu.com', '/c/c/forum/sign')
ALLOWED = {TBS, LIKE, SIGN}
BASE = {'_client_type': '2', '_client_version': '9.7.8.0',
        '_phone_imei': '000000000000000', 'model': 'MI+5', 'net_type': '1'}

class Stop(Exception):
    pass


def request(endpoint, bduss, fields=None):
    if endpoint not in ALLOWED:
        raise Stop()
    host, path = endpoint
    headers = {'User-Agent': 'Mozilla/5.0', 'Cookie': 'BDUSS=' + bduss,
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
        if response.status != 200:
            raise Stop()
        raw = response.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise Stop()
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise Stop()
        return result
    finally:
        conn.close()


def run(bduss):
    if not bduss or not re.fullmatch(r'[A-Za-z0-9_~.%+/=\-]+', bduss):
        raise Stop()
    auth = request(TBS, bduss)
    if str(auth.get('is_login')) != '1' or not isinstance(auth.get('tbs'), str) or not auth['tbs']:
        raise Stop()
    forums = {}
    for page in range(1, 51):
        result = request(LIKE, bduss, dict(BASE, _client_id='wappc_1534235498291_488',
            **{'from': '1008621y'}, page_no=str(page), page_size='200',
            timestamp=str(int(time.time())), vcode_tag='11'))
        if str(result.get('error_code', '0')) != '0' or not isinstance(result.get('forum_list'), dict):
            raise Stop()
        for kind in ('non-gconforum', 'gconforum'):
            items = result['forum_list'].get(kind, [])
            if isinstance(items, dict):
                items = [items]
            if not isinstance(items, list):
                raise Stop()
            for item in items:
                fid, name = str(item['id']), item['name']
                if not fid.isdigit() or not isinstance(name, str) or not name:
                    raise Stop()
                forums[fid] = name
        more = str(result.get('has_more', '0'))
        if more == '0':
            break
        if more != '1':
            raise Stop()
        time.sleep(2)
    else:
        raise Stop()
    incomplete = False
    for fid, name in forums.items():
        time.sleep(2)
        result = request(SIGN, bduss, dict(BASE, fid=fid, kw=name, tbs=auth['tbs'],
            timestamp=str(int(time.time()))))
        status = str(result.get('error_code', ''))
        if status == '340006':
            incomplete = True
        elif status not in ('0', '160002'):
            raise Stop()
    if incomplete:
        raise Stop()


def main():
    try:
        run(os.environ.pop('BDUSS', ''))
    except Exception:
        print('Task incomplete. Check your account manually.')
        return 1
    print('Task completed.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
