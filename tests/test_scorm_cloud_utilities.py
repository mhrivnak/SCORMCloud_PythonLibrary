from base_test_case import BaseTestCase
import client

class TestScormCloudUtilities(BaseTestCase):
    def test_clean_cloud_host_url(self):
        """make sure this method doesn't screw with the perfectly correct URL"""
        ret = client.ScormCloudUtilities.clean_cloud_host_url(self.config.serviceurl)
        self.assertEqual(ret, self.config.serviceurl)
