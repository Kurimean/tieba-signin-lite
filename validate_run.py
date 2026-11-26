"""Explicit validation only: no padding, no per-account output or raw errors."""
import os
import pathlib
import subprocess
import sys

CATEGORIES = {
    0: 'OK', 10: 'CREDENTIAL_FORMAT', 11: 'AUTH_REJECTED', 12: 'AUTH_REQUEST',
    13: 'LIST_REQUEST', 14: 'NO_ACCESSIBLE_FORUM', 15: 'SIGN_REQUEST',
    16: 'UNEXPECTED',
}
TIMEOUT_SECONDS = 280


def check(secret):
    try:
        result = subprocess.run(
            [sys.executable, '-I', '-B', str(pathlib.Path(__file__).resolve().with_name('signin.py')), '--diagnose'],
            env={'BDUSS': secret, 'PATH': os.defpath},
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=TIMEOUT_SECONDS, check=False,
        )
        return CATEGORIES.get(result.returncode, 'UNEXPECTED')
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'
    except Exception:
        return 'UNEXPECTED'


def main():
    first = os.environ.pop('BDUSS', '')
    second = os.environ.pop('BDUSS_SECOND', '')
    if not first or not second or first == second:
        print('Validation incomplete. CREDENTIAL_CONFIGURATION')
        return 1
    outcomes = {check(first), check(second)}
    first = second = None
    if outcomes == {'OK'}:
        print('Validation completed.')
        return 0
    print('Validation incomplete. ' + ', '.join(sorted(outcomes - {'OK'})))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
