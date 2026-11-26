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

    @patch('signin.time.sleep')
    @patch('signin.request')
    def test_success(self, req, sleep):
        req.side_effect = [{'error_code': 0, 'anti': {'tbs':'fake'}},
            {'forum_list': {'non-gconforum':[{'id':'1','name':'private'}]}, 'has_more':'0'},
            {'error_code':'160002'}]
        signin.run('fake')
        self.assertEqual(req.call_count, 3)

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

    @patch('signin.run', side_effect=ValueError('SECRET private forum'))
    def test_no_exception_leak(self, run):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(signin.main(), 1)
        self.assertEqual(buf.getvalue(), 'Task incomplete. Check your account manually.\n')

if __name__ == '__main__':
    unittest.main()
