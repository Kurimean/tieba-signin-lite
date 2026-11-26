"""Read-only status check. Never sends sign-in requests or logs account data."""
import http.client
import json
import os
import re
import ssl
from urllib.parse import urlencode

HOST = 'tieba.baidu.com'
PATH = '/c/f/forum/forumGuide'


def classify(data):
    if not isinstance(data, dict):
        return 'STATUS_UNKNOWN'
    if str(data.get('error_code', '')) != '0':
        return 'STATUS_REJECTED'
    if str(data.get('is_login', '')) != '1':
        return 'STATUS_AUTH_UNKNOWN'
    forums = data.get('like_forum')
    if not isinstance(forums, list) or not forums:
        return 'STATUS_UNKNOWN'
    if any(not isinstance(f, dict) for f in forums):
        return 'STATUS_UNKNOWN'
    for f in forums:
        if str(f.get('is_forbidden', '0')) == '1':
            continue
        if str(f.get('is_sign', '')) == '0':
            return 'UNSIGNED_PRESENT'
    if data.get('like_forum_has_more') not in (False, 0, '0'):
        return 'STATUS_PARTIAL'
    accessible = [f for f in forums if str(f.get('is_forbidden', '0')) != '1']
    if accessible and all(str(f.get('is_sign', '')) == '1' for f in accessible):
        return 'SIGNED_REPORTED'
    return 'STATUS_UNKNOWN'


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
        return classify(json.loads(raw))
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
