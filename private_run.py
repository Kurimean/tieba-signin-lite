"""Run sign-in with a bounded, padded execution window and no child output."""
import os
import pathlib
import subprocess
import sys
import time

WINDOW_SECONDS = 300
WORK_LIMIT_SECONDS = 280


def main():
    started = time.monotonic()
    secret = os.environ.pop('BDUSS', '')
    success = False
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
        remaining = max(0.0, WINDOW_SECONDS - (time.monotonic() - started))
        time.sleep(remaining)
    print('Task completed.' if success else 'Task incomplete.')
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
