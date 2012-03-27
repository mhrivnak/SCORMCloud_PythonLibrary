from base_test_case import BaseTestCase
from client import Configuration

from testlib import network_test

class TestPing(BaseTestCase):
    """test actual pings to the live API server"""

    @network_test
    def test_ping(self):
        """test the ping method in its natural form"""
        self.assertTrue(self.service.debug_service.ping())

    @network_test
    def test_authping(self):
        """test the authping method in its natural form"""
        self.assertTrue(self.service.debug_service.authping())

    @network_test
    def test_auth_fail(self):
        """fail because secret is incorrect, which raises ScormCloudError"""
        # need a new object so we don't clobber the global one
        self.service.config = Configuration(self.config.appid,
            'not a secret', self.config.serviceurl)
        self.assertFalse(self.service.debug_service.authping())

    @network_test
    def test_url_fail(self):
        """fail because URL is incorrect, which raises an IOError"""
        # need a new object so we don't clobber the global one
        self.service.config = Configuration(self.config.appid,
            self.config.secret, 'http://not.aworkingurl/')
        self.assertFalse(self.service.debug_service.authping())
