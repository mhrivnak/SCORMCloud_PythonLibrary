try:
    import unittest2 as unittest
except ImportError:
    import unittest

from client import *
from . import settings

class BaseTestCase(unittest.TestCase):
    config = Configuration(settings.APPID, settings.SECRET, settings.URL)

    def setUp(self):
        self.service = ScormCloudService(self.config)
        self.request = self.service.request()
