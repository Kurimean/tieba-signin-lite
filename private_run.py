"""Run two isolated account slots, with constant time and aggregate output."""
import os
import pathlib
import subprocess
import sys
import time

WINDOW_SECONDS = 930
WORK_LIMIT_SECONDS = 900


def run_slot(secret, required=False):
    started = time.monotonic()
    success = not required
    try:
        if secret:
            result = subprocess.run(
                [sys.executable, '-I', '-B', str(pathlib.Path(__file__).resolve().with_name('signin.py'))],
                env={'BDUSS': secret, 'PATH': os.defpath},
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=WORK_LIMIT_SECONDS, check=False,
            )
            success = result.returncode == 0
    except Exception:
        success = False
    finally:
        secret = None
        time.sleep(max(0.0, WINDOW_SECONDS - (time.monotonic() - started)))
    return success


def main():
    first = os.environ.pop('BDUSS', '')
    second = os.environ.pop('BDUSS_SECOND', '')
    # The workflow falls back to the first secret for an unconfigured slot.
    # Never sign the same credential twice; still pad the unused slot.
    if second == first:
        second = ''
    first_ok = run_slot(first, required=True)
    first = None
    second_ok = run_slot(second)
    second = None
    success = first_ok and second_ok
    print('Task completed.' if success else 'Task incomplete.')
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
