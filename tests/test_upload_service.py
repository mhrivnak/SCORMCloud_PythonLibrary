import urlparse

from mock import patch, MagicMock

from base_test_case import BaseTestCase
import client
from testlib import network_test

class TestUploadService(BaseTestCase):
    """test actual pings to the live API server"""

    @network_test
    def test_get_upload_token(self):
        """get an actual upload token from the server"""
        ret = self.service.upload_service.get_upload_token()
        self.assertIsInstance(ret, client.UploadToken)
        self.assertIsInstance(ret.tokenid, basestring)
        self.assertIsInstance(ret.server, basestring)

    def test_get_upload_url(self):
        """test building an upload URL"""
        SERVER = 'cloud.scorm.com'
        TOKENID = 'abc123'
        CALLBACKURL = 'http://fake.url/'
        get_upload_token_mock = MagicMock(return_value=client.UploadToken(SERVER, TOKENID))
        with patch('client.UploadService.get_upload_token', get_upload_token_mock):
            ret = self.service.upload_service.get_upload_url(CALLBACKURL)
            parts = urlparse.urlparse(ret)
            config_parts = urlparse.urlparse(self.config.serviceurl)
            for i in range(2):
                self.assertEqual(parts[i], config_parts[i])
            self.assertIn(TOKENID, parts.query)
