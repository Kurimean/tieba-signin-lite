import contextlib
import io
import os
import unittest
from unittest.mock import patch
import verify_status as v


class StatusTests(unittest.TestCase):
    def status(self, entries, more=False):
        return v.classify({'error_code': 0, 'is_login': 1,
                           'like_forum': entries, 'like_forum_has_more': more})

    def test_complete(self):
        self.assertEqual(self.status([{'is_sign': 1}, {'is_forbidden': 1}]), 'SIGNED_REPORTED')

    def test_incomplete(self):
        self.assertEqual(self.status([{'is_sign': 0}]), 'UNSIGNED_PRESENT')

    def test_partial_list_cannot_pass(self):
        self.assertEqual(self.status([{'is_sign': 1}], True), 'STATUS_PARTIAL')

    def test_unknown_flag_cannot_pass(self):
        self.assertEqual(self.status([{}]), 'STATUS_UNKNOWN')

    def test_rejected(self):
        self.assertEqual(v.classify({'error_code': 1}), 'STATUS_REJECTED')

    @patch('verify_status.http.client.HTTPSConnection')
    def test_never_follows_redirect(self, connect):
        conn = connect.return_value
        conn.getresponse.return_value.status = 302
        self.assertEqual(v.check('fake'), 'STATUS_HTTP')
        self.assertEqual(conn.request.call_args.args[:2], ('POST', v.PATH))
        connect.assert_called_once()
        conn.close.assert_called_once()

    @patch('verify_status.check', side_effect=['SIGNED_REPORTED', 'UNSIGNED_PRESENT'])
    def test_aggregate_only(self, check):
        buf = io.StringIO()
        with patch.dict(os.environ, {'BDUSS': 'one', 'BDUSS_SECOND': 'two'}), contextlib.redirect_stdout(buf):
            self.assertEqual(v.main(), 1)
        self.assertEqual(buf.getvalue(), 'Status verification incomplete. UNSIGNED_PRESENT\n')
        self.assertEqual(check.call_count, 2)


if __name__ == '__main__':
    unittest.main()
