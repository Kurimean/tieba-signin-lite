import contextlib
import io
import unittest
from unittest.mock import patch
import signin

class Tests(unittest.TestCase):
    def test_unapproved_endpoint(self):
        with self.assertRaises(signin.Stop):
            signin.request(('example.org', '/'), 'fake')

    @patch('signin.http.client.HTTPSConnection')
    def test_redirect_fails(self, connect):
        conn = connect.return_value
        conn.getresponse.return_value.status = 302
        conn.getresponse.return_value.getheader.return_value = 'https://example.org/'
        with self.assertRaises(signin.Stop) as exc:
            signin.request(signin.TBS, 'fake')
        self.assertEqual(exc.exception.code, 'AUTH_REDIRECT_OTHER')
        connect.assert_called_once()
        conn.close.assert_called_once()

    @patch('signin.http.client.HTTPSConnection')
    def test_connection_reused(self, connect):
        conn = connect.return_value
        conn.host = signin.TBS[0]
        conn.getresponse.return_value.status = 200
        conn.getresponse.return_value.read.return_value = b'{"error_code":"0"}'
        for endpoint in (signin.TBS, signin.LIKE, signin.SIGN):
            self.assertEqual(signin.request(endpoint, 'fake', {}, connection=conn),
                             {'error_code': '0'})
        connect.assert_not_called()
        self.assertEqual(conn.request.call_count, 3)
        conn.close.assert_not_called()

    @patch('signin.http.client.HTTPSConnection')
    def test_wrong_connection_host_rejected(self, connect):
        conn = connect.return_value
        conn.host = 'example.org'
        with self.assertRaises(signin.Stop):
            signin.request(signin.TBS, 'fake', {}, connection=conn)
        conn.request.assert_not_called()

    @patch('signin.http.client.HTTPSConnection')
    @patch('signin.time.sleep')
    @patch('signin.request')
    def test_success(self, req, sleep, connect):
        req.side_effect = [{'error_code': 0, 'anti': {'tbs':'fake'}},
            {'forum_list': {'non-gconforum':[{'id':'1','name':'private'}]}, 'has_more':'0'},
            {'error_code':'160002'}]
        signin.run('fake')
        self.assertEqual(req.call_count, 3)
        connect.assert_called_once()
        for call in req.call_args_list:
            self.assertIs(call.kwargs['connection'], connect.return_value)
        connect.return_value.close.assert_called_once()

    @patch('signin.request')
    def test_bad_login_stops(self, req):
        req.return_value = {'error_code': 1}
        with self.assertRaises(signin.Stop):
            signin.run('fake')
        req.assert_called_once()

    @patch('signin.time.sleep')
    @patch('signin.request')
    def test_unknown_status_stops(self, req, sleep):
        req.side_effect = [{'error_code': 0, 'anti': {'tbs':'fake'}},
            {'forum_list': {'non-gconforum':[{'id':'1','name':'private'}, {'id':'2','name':'private2'}]}},
            {'error_code':'unknown', 'error_msg':'private'}]
        with self.assertRaises(signin.Stop):
            signin.run('fake')
        self.assertEqual(req.call_count, 3)

    @patch('signin.time.sleep')
    @patch('signin.request')
    def test_unavailable_forum_skipped(self, req, sleep):
        req.side_effect = [{'error_code': 0, 'anti': {'tbs':'fake'}},
            {'forum_list': {'non-gconforum':[{'id':'1','name':'private'}, {'id':'2','name':'private2'}]}},
            {'error_code':'340006'}, {'error_code':'0'}]
        self.assertTrue(signin.run('fake'))
        self.assertEqual(req.call_count, 4)

    @patch('signin.time.sleep')
    @patch('signin.request')
    def test_all_unavailable_fails(self, req, sleep):
        req.side_effect = [{'error_code': 0, 'anti': {'tbs':'fake'}},
            {'forum_list': {'non-gconforum':[{'id':'1','name':'private'}]}},
            {'error_code':'340006'}]
        with self.assertRaises(signin.Stop) as exc:
            signin.run('fake')
        self.assertEqual(exc.exception.code, 'SIGN_UNAVAILABLE')

    @patch('signin.run', side_effect=ValueError('SECRET private forum'))
    def test_no_exception_leak(self, run):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(signin.main(), 1)
        self.assertEqual(buf.getvalue(), 'Task incomplete. Check your account manually.\n')

    @patch('signin.run')
    def test_confirmed_complete_skips_all_writes(self, run):
        with patch.dict('os.environ', {'BDUSS': 'fake'}), patch('builtins.print'):
            self.assertEqual(signin.main(verifier=lambda secret: 'SIGNED_REPORTED'), 0)
        run.assert_not_called()

    @patch('signin.run', side_effect=signin.Stop('SIGN_REJECTED'))
    def test_rejected_but_complete_is_reconciled(self, run):
        from unittest.mock import Mock
        verifier = Mock(side_effect=['UNSIGNED_PRESENT', 'SIGNED_REPORTED'])
        with patch.dict('os.environ', {'BDUSS': 'fake'}), patch('builtins.print'):
            self.assertEqual(signin.main(diagnostic=True, verifier=verifier), 0)
        run.assert_called_once_with('fake')
        self.assertEqual(verifier.call_count, 2)

    @patch('signin.run', side_effect=signin.Stop('SIGN_REJECTED'))
    def test_partial_does_not_override_rejection(self, run):
        with patch.dict('os.environ', {'BDUSS': 'fake'}), patch('builtins.print'):
            self.assertEqual(signin.main(diagnostic=True, verifier=lambda secret: 'STATUS_PARTIAL'), 20)
        run.assert_called_once_with('fake')

    @patch('signin.run', side_effect=signin.Stop('AUTH_REJECTED'))
    def test_auth_rejection_not_reconciled(self, run):
        from unittest.mock import Mock
        verifier = Mock(side_effect=['STATUS_UNKNOWN', 'SIGNED_REPORTED'])
        with patch.dict('os.environ', {'BDUSS': 'fake'}):
            self.assertEqual(signin.main(diagnostic=True, verifier=verifier), 11)
        self.assertEqual(verifier.call_count, 1)

if __name__ == '__main__':
    unittest.main()
