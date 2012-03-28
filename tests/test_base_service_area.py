from cStringIO import StringIO

from mock import patch, MagicMock

from client import *
from base_test_case import BaseTestCase

class TestBaseServiceArea(BaseTestCase):
    XML_RESPONSE = '<?xml version="1.0" encoding="utf-8" ?><rsp stat="ok"></rsp>'
    METHOD_PARAMS = {'x':'foo', 'y':'bar'}

    def test_build_params(self):
        PARAMS = self.METHOD_PARAMS.copy()
        PARAMS.update({'z' : None, 'self' : BaseServiceArea(self.service)})
        ret = BaseServiceArea.build_params(PARAMS)
        for key in self.METHOD_PARAMS:
            self.assertIn(key, ret)
            self.assertEqual(ret[key], self.METHOD_PARAMS[key])
        self.assertNotIn('z', ret)
        self.assertNotIn('self', ret)

    def test_build_and_make_call(self):
        """
        Call the build_and_make_call method with a method name and additional
        parameters. Verify that urllib2.urlopen gets called and that the
        encoded parameters include the method name and the additional
        parameters. Also verify that it excludes parameters whose value is
        None or key == 'self'.
        """

        METHOD_NAME = 'imaginary_method'
        mock_urlopen = MagicMock(return_value=StringIO(self.XML_RESPONSE))

        class FakeServiceArea(BaseServiceArea):
            def fake_method(self, x, y, z=None):
                return self.build_and_make_call(METHOD_NAME, locals())

        with patch('urllib2.urlopen', mock_urlopen):
            FakeServiceArea(self.service).fake_method(**self.METHOD_PARAMS)
                
        self.assertTrue(mock_urlopen.called)
        call_args, call_kwargs = mock_urlopen.call_args
        self.assertEqual(call_kwargs, {})
        self.assertEqual(len(call_args), 2)
        # call_args[1] is the string result of urlencoding the parameters
        self.assertIn('method=%s' % METHOD_NAME, call_args[1])
        for key in self.METHOD_PARAMS:
            self.assertIn('%s=%s' % (key, self.METHOD_PARAMS[key]), call_args[1])
        self.assertNotIn('z=', call_args[1])
        self.assertNotIn('self=', call_args[1])
