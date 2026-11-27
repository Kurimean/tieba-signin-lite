"""One-click sign-in experiment. No fallback or replay on rejection."""
import http.client
import json
import os
import pathlib
import re
import ssl
import sys
from urllib.parse import urlencode

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import verify_status

HOST = 'tieba.baidu.com'
PATH = '/c/c/forum/msign'


def parse_result(data):
    if not isinstance(data, dict) or 'error_code' not in data:
        return 19
    code = str(data['error_code'])
    if code != '0':
        return 28 if code == '340011' else 20
    if 'error' in data:
        nested = data['error']
        if not isinstance(nested, dict) or 'errno' not in nested:
            return 19
        code = str(nested['errno'])
        if code != '0':
            return 28 if code == '340011' else 20
    return 0


def submit(secret):
    if not secret or not re.fullmatch(r'[A-Za-z0-9_~.%+/=\-]+', secret):
        return 10
    conn = None
    try:
        conn = http.client.HTTPSConnection(HOST, timeout=15, context=ssl.create_default_context())
        body = urlencode({'_client_version': '22.15.1.0', 'subapp_type': 'hybrid'}).encode()
        conn.request('POST', PATH, body, {
            'Cookie': 'BDUSS=' + secret,
            'User-Agent': 'tieba-signin-lite',
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Subapp-Type': 'hybrid',
            'Referer': 'https://tieba.baidu.com/',
        })
        res = conn.getresponse()
        if res.status != 200:
            return 18
        raw = res.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            return 19
        return parse_result(json.loads(raw))
    except (OSError, http.client.HTTPException):
        return 17
    except Exception:
        return 19
    finally:
        if conn is not None:
            conn.close()


def main():
    secret = os.environ.pop('BDUSS', '')
    if not secret or not re.fullmatch(r'[A-Za-z0-9_~.%+/=\-]+', secret):
        return 10
    before = verify_status.check(secret)
    if before == 'SIGNED_REPORTED':
        return 0
    if before != 'UNSIGNED_PRESENT':
        return 27
    result = submit(secret)
    after = verify_status.check(secret)
    if after == 'SIGNED_REPORTED':
        return 0
    return result if result else 26


if __name__ == '__main__':
    raise SystemExit(main())
