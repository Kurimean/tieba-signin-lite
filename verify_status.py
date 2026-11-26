"""Read-only status check. Never sends sign-in requests or logs account data."""
import http.client
import json
import os
import re
import ssl
import pathlib
import sys
from urllib.parse import urlencode

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import signin

HOST = 'tieba.baidu.com'
PATH = '/c/f/forum/forumGuide'


def classify(data, expected_ids=None):
    if not isinstance(data, dict):
        return 'STATUS_UNKNOWN'
    if str(data.get('error_code', '')) != '0':
        return 'STATUS_REJECTED'
    if str(data.get('is_login', '')) != '1':
        return 'STATUS_AUTH_UNKNOWN'
    forums = data.get('like_forum')
    if not isinstance(forums, list) or not forums:
        return 'STATUS_UNKNOWN'
    reported = {}
    for f in forums:
        if not isinstance(f, dict):
            return 'STATUS_UNKNOWN'
        fid = str(f.get('forum_id', ''))
        if not fid.isdigit() or fid in reported:
            return 'STATUS_UNKNOWN'
        reported[fid] = f
    if any(str(f.get('is_sign', '')) == '0' and
           str(f.get('is_forbidden', '0')) != '1' for f in reported.values()):
        return 'UNSIGNED_PRESENT'
    if not expected_ids or set(reported) != set(expected_ids):
        return 'STATUS_PARTIAL'
    accessible = [f for f in reported.values() if str(f.get('is_forbidden', '0')) != '1']
    if accessible and all(str(f.get('is_sign', '')) == '1' for f in accessible):
        return 'SIGNED_REPORTED'
    return 'STATUS_UNKNOWN'


def read_expected(secret):
    conn = http.client.HTTPSConnection(signin.LIKE[0], timeout=15, context=ssl.create_default_context())
    try:
        return set(signin.list_followed(secret, conn, strict=True))
    finally:
        conn.close()


def check(secret):
    if not secret or not re.fullmatch(r'[A-Za-z0-9_~.%+/=\-]+', secret):
        return 'CREDENTIAL_CONFIGURATION'
    conn = None
    try:
        conn = http.client.HTTPSConnection(HOST, timeout=15, context=ssl.create_default_context())
        body = urlencode({'sort_type': 3, 'call_from': 3}).encode()
        conn.request('POST', PATH, body, {
            'Cookie': 'BDUSS=' + secret,
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Subapp-Type': 'hybrid',
            'Referer': 'https://tieba.baidu.com/',
        })
        response = conn.getresponse()
        if response.status != 200:
            return 'STATUS_HTTP'
        raw = response.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            return 'STATUS_UNKNOWN'
        data = json.loads(raw)
        preliminary = classify(data)
        if preliminary != 'STATUS_PARTIAL':
            return preliminary
        conn.close()
        conn = None
        try:
            expected = read_expected(secret)
        except Exception:
            return 'COVERAGE_UNKNOWN'
        return classify(data, expected)
    except Exception:
        return 'STATUS_UNKNOWN'
    finally:
        if conn is not None:
            conn.close()


def main():
    first = os.environ.pop('BDUSS', '')
    second = os.environ.pop('BDUSS_SECOND', '')
    if not first or not second or first == second:
        print('Status verification incomplete. CREDENTIAL_CONFIGURATION')
        return 1
    outcomes = {check(first), check(second)}
    first = second = None
    if outcomes == {'SIGNED_REPORTED'}:
        print('Status verification: both reported complete.')
        return 0
    print('Status verification incomplete. ' + ', '.join(sorted(outcomes - {'SIGNED_REPORTED'})))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
