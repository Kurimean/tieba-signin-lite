import contextlib
import io
import os
import subprocess
import unittest
from unittest.mock import patch, Mock
import private_run

class PrivateRunTests(unittest.TestCase):
    def simulate(self, duration, returncode=0, exception=None, secret='fake-credential'):
        with patch.dict(os.environ, {'BDUSS': secret}, clear=False), \
             patch('private_run.time.monotonic', side_effect=[1000, 1000+duration]), \
             patch('private_run.time.sleep') as sleep, \
             patch('private_run.subprocess.run') as run:
            if exception:
                run.side_effect = exception
            else:
                run.return_value = Mock(returncode=returncode)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                result = private_run.main()
            self.assertNotIn('BDUSS', os.environ)
            sleep.assert_called_once_with(max(0, 300-duration))
            if secret:
                kwargs = run.call_args.kwargs
                self.assertEqual(kwargs['stdout'], subprocess.DEVNULL)
                self.assertEqual(kwargs['stderr'], subprocess.DEVNULL)
                self.assertEqual(kwargs['timeout'], 280)
                self.assertEqual(kwargs['env']['BDUSS'], secret)
                self.assertNotIn(secret, str(run.call_args.args))
            else:
                run.assert_not_called()
            return result, buf.getvalue()

    def test_success_is_padded(self):
        self.assertEqual(self.simulate(143), (0, 'Task completed.\n'))

    def test_failure_is_padded(self):
        self.assertEqual(self.simulate(2, returncode=1), (1, 'Task incomplete.\n'))

    def test_timeout_is_padded(self):
        self.assertEqual(self.simulate(280, exception=subprocess.TimeoutExpired('private', 280)),
                         (1, 'Task incomplete.\n'))

    def test_exception_does_not_leak(self):
        self.assertEqual(self.simulate(1, exception=ValueError('private credential')),
                         (1, 'Task incomplete.\n'))

    def test_missing_secret_is_padded(self):
        self.assertEqual(self.simulate(0, secret=''), (1, 'Task incomplete.\n'))

if __name__ == '__main__':
    unittest.main()
