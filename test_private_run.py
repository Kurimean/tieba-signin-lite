import contextlib
import io
import os
import subprocess
import unittest
from unittest.mock import patch, Mock
import private_run


class PrivateRunTests(unittest.TestCase):
    def simulate(self, first='fake-one', second='', outcomes=(0, 0)):
        with patch.dict(os.environ, {'BDUSS': first, 'BDUSS_SECOND': second}, clear=False), \
             patch('private_run.time.monotonic', side_effect=[1000, 1143, 1300, 1302]), \
             patch('private_run.time.sleep') as sleep, \
             patch('private_run.subprocess.run') as run:
            run.side_effect = [x if isinstance(x, Exception) else Mock(returncode=x) for x in outcomes]
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                result = private_run.main()
            self.assertNotIn('BDUSS', os.environ)
            self.assertNotIn('BDUSS_SECOND', os.environ)
            self.assertEqual([c.args[0] for c in sleep.call_args_list], [157, 298])
            expected = [s for s in (first, second if second != first else '') if s]
            self.assertEqual(run.call_count, len(expected))
            for call, secret in zip(run.call_args_list, expected):
                kwargs = call.kwargs
                self.assertEqual(kwargs['stdout'], subprocess.DEVNULL)
                self.assertEqual(kwargs['stderr'], subprocess.DEVNULL)
                self.assertEqual(kwargs['timeout'], 280)
                self.assertEqual(kwargs['env'], {'BDUSS': secret, 'PATH': os.defpath})
                self.assertNotIn(secret, str(call.args))
            return result, buf.getvalue()

    def test_one_account(self):
        self.assertEqual(self.simulate(), (0, 'Task completed.\n'))

    def test_duplicate_fallback_not_signed_twice(self):
        self.assertEqual(self.simulate(second='fake-one'), (0, 'Task completed.\n'))

    def test_two_accounts_isolated(self):
        self.assertEqual(self.simulate(second='fake-two'), (0, 'Task completed.\n'))

    def test_first_failure_does_not_skip_second(self):
        self.assertEqual(self.simulate(second='fake-two', outcomes=(1, 0)), (1, 'Task incomplete.\n'))

    def test_second_failure_is_aggregate_failure(self):
        self.assertEqual(self.simulate(second='fake-two', outcomes=(0, 1)), (1, 'Task incomplete.\n'))

    def test_timeout_does_not_leak(self):
        self.assertEqual(self.simulate(second='fake-two', outcomes=(subprocess.TimeoutExpired('private', 280), 0)),
                         (1, 'Task incomplete.\n'))

    def test_exception_does_not_leak(self):
        self.assertEqual(self.simulate(outcomes=(ValueError('private credential'),)),
                         (1, 'Task incomplete.\n'))

    def test_required_secret_missing(self):
        self.assertEqual(self.simulate(first='', second='fake-two'), (1, 'Task incomplete.\n'))

    def test_no_credentials(self):
        self.assertEqual(self.simulate(first=''), (1, 'Task incomplete.\n'))


if __name__ == '__main__':
    unittest.main()
