import contextlib
import io
import os
import subprocess
import unittest
from unittest.mock import Mock, patch
import signin
import validate_run


class ValidationTests(unittest.TestCase):
    def simulate(self, first, second, results):
        buf = io.StringIO()
        with patch.dict(os.environ, {'BDUSS': first, 'BDUSS_SECOND': second}), \
             patch('validate_run.subprocess.run', side_effect=[
                 x if isinstance(x, Exception) else Mock(returncode=x) for x in results
             ]) as run, contextlib.redirect_stdout(buf):
            rc = validate_run.main()
            self.assertNotIn('BDUSS', os.environ)
            self.assertNotIn('BDUSS_SECOND', os.environ)
            for call in run.call_args_list:
                self.assertEqual(call.kwargs['stdout'], subprocess.DEVNULL)
                self.assertEqual(call.kwargs['stderr'], subprocess.DEVNULL)
                self.assertEqual(set(call.kwargs['env']), {'BDUSS', 'PATH'})
                self.assertEqual(call.kwargs['timeout'], 900)
            return rc, buf.getvalue(), run.call_count

    def test_success(self):
        self.assertEqual(self.simulate('one', 'two', [0, 0]), (0, 'Validation completed.\n', 2))

    def test_duplicate(self):
        self.assertEqual(self.simulate('one', 'one', []), (1, 'Validation incomplete. CREDENTIAL_CONFIGURATION\n', 0))

    def test_missing(self):
        self.assertEqual(self.simulate('one', '', []), (1, 'Validation incomplete. CREDENTIAL_CONFIGURATION\n', 0))

    def test_aggregate_no_account_order(self):
        expected = (1, 'Validation incomplete. AUTH_REJECTED\n', 2)
        self.assertEqual(self.simulate('one', 'two', [0, 11]), expected)
        self.assertEqual(self.simulate('one', 'two', [11, 0]), expected)

    def test_timeout_no_secret(self):
        self.assertEqual(self.simulate('one', 'two', [subprocess.TimeoutExpired('private', 900), 0]),
                         (1, 'Validation incomplete. TIMEOUT\n', 2))

    def test_diagnostic_exit_codes(self):
        with patch('signin.run', side_effect=signin.Stop('AUTH_REJECTED')):
            self.assertEqual(signin.main(diagnostic=True), 11)
        with patch('signin.run', side_effect=signin.Stop('SIGN_UNAVAILABLE')):
            self.assertEqual(signin.main(diagnostic=True), 14)
        for category, code in [('SIGN_NETWORK', 17), ('SIGN_HTTP', 18), ('SIGN_RESPONSE', 19), ('SIGN_REJECTED', 20), ('STATUS_POSTCHECK', 26), ('STATUS_PRECHECK', 27)]:
            with patch('signin.run', side_effect=signin.Stop(category)):
                self.assertEqual(signin.main(diagnostic=True), code)
            self.assertEqual(self.simulate('one', 'two', [0, code]), (1, 'Validation incomplete. ' + validate_run.CATEGORIES[code] + '\n', 2))

if __name__ == '__main__':
    unittest.main()
