import os
import unittest
from unittest.mock import patch
import batch_signin as b


class BatchTests(unittest.TestCase):
    def test_response(self):
        self.assertEqual(b.parse_result({'error_code': 0, 'error': {'errno': 0}}), 0)
        self.assertEqual(b.parse_result({'error_code': 0, 'error': {'errno': 340011}}), 28)
        self.assertEqual(b.parse_result({'error_code': 340011}), 28)
        self.assertEqual(b.parse_result({'error_code': 1}), 20)
        self.assertEqual(b.parse_result({'error_code': 0, 'error': {}}), 19)

    @patch('batch_signin.submit')
    @patch('batch_signin.verify_status.check', return_value='SIGNED_REPORTED')
    def test_already_complete(self, check, submit):
        with patch.dict(os.environ, {'BDUSS': 'fake'}):
            self.assertEqual(b.main(), 0)
        submit.assert_not_called()

    @patch('batch_signin.submit', return_value=0)
    @patch('batch_signin.verify_status.check', side_effect=['UNSIGNED_PRESENT', 'SIGNED_REPORTED'])
    def test_complete(self, check, submit):
        with patch.dict(os.environ, {'BDUSS': 'fake'}):
            self.assertEqual(b.main(), 0)
        submit.assert_called_once_with('fake')

    @patch('batch_signin.submit', return_value=28)
    @patch('batch_signin.verify_status.check', return_value='UNSIGNED_PRESENT')
    def test_rejection_never_replays(self, check, submit):
        with patch.dict(os.environ, {'BDUSS': 'fake'}):
            self.assertEqual(b.main(), 28)
        submit.assert_called_once()

    @patch('batch_signin.submit', return_value=0)
    @patch('batch_signin.verify_status.check', return_value='UNSIGNED_PRESENT')
    def test_unconfirmed_write_fails(self, check, submit):
        with patch.dict(os.environ, {'BDUSS': 'fake'}):
            self.assertEqual(b.main(), 26)
        submit.assert_called_once()

    @patch('batch_signin.submit')
    @patch('batch_signin.verify_status.check', return_value='STATUS_PARTIAL')
    def test_unknown_never_writes(self, check, submit):
        with patch.dict(os.environ, {'BDUSS': 'fake'}):
            self.assertEqual(b.main(), 27)
        submit.assert_not_called()

    @patch('batch_signin.http.client.HTTPSConnection')
    def test_redirect_not_followed(self, connect):
        conn = connect.return_value
        conn.getresponse.return_value.status = 302
        self.assertEqual(b.submit('fake'), 18)
        conn.request.assert_called_once()
        conn.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
