import datetime
from xml.dom import minidom
from cStringIO import StringIO

from mock import patch, MagicMock

from client import *
from . import settings
from base_test_case import BaseTestCase

class TestServiceRequest(BaseTestCase):
    PING_XML_RESPONSE = '<?xml version="1.0" encoding="utf-8" ?><rsp stat="ok"><pong /></rsp>'

    def test_auth_dict(self):
        ret = self.request.auth_dict
        self.assertEqual(ret['appid'], settings.APPID)
        self.assertEqual(ret['origin'], self.config.origin)
        self.assertEqual(ret['applib'], 'python')
        current_year = str(datetime.datetime.utcnow().year)
        self.assertTrue(ret['ts'].startswith(current_year))

    def test_encode_and_sign(self):
        params = {'method' : 'rustici.debug.ping'}
        params.update(self.request.auth_dict)
        ret = self.request._encode_and_sign(params, settings.SECRET)
        # make sure all parameters are included
        for key in params:
            self.assertIn('%s=%s' % (key, params[key]), ret)
        # make sure the signature is included
        self.assertIn('sig=', ret)

    def test_get_xml_ok(self):
        """test the get_xml method with XML from a successful call"""
        self.assertIsInstance(self.request.get_xml(self.PING_XML_RESPONSE), minidom.Document)

    def test_get_xml_fail(self):
        """test the get_xml method with XML from a failed call"""
        XML = '<?xml version="1.0" encoding="utf-8" ?><rsp stat="fail"><err code="678" msg="wah wah waaaaaahhhh" /></rsp>'
        self.assertRaises(ScormCloudError, self.request.get_xml, XML)

    def test_send_post(self):
        """verify that the send_post method correctly calls urlopen and get_xml"""
        CALL_ARGS = 'x=2&y=3'
        mock_urlopen = MagicMock(return_value=StringIO(self.PING_XML_RESPONSE))
        with patch('urllib2.urlopen', mock_urlopen):
            ret = self.request.send_post(self.config.serviceurl, CALL_ARGS)
            self.assertEqual(ret, self.PING_XML_RESPONSE)

        self.assertTrue(mock_urlopen.called)
        call_args, call_kwargs = mock_urlopen.call_args
        self.assertEqual(call_kwargs, {})
        self.assertEqual(len(call_args), 2)
        # call_args[0] is the URL
        self.assertEqual(call_args[0], self.config.serviceurl)
        # call_args[1] is the string result of urlencoding the parameters
        self.assertEqual(call_args[1], CALL_ARGS)

    def test_call_service(self):
        """
        Call the test_call_service method with a method name and additional
        parameters. Verify that urllib2.urlopen gets called and that the
        encoded parameters include the method name and the additional
        parameters. Also verify that it returns whatever get_xml returns.
        """

        METHOD_NAME = 'imaginary_method'
        METHOD_PARAMS = {'x':'foo', 'y':'bar'}
        mock_urlopen = MagicMock(return_value=StringIO(self.PING_XML_RESPONSE))

        with patch('urllib2.urlopen', mock_urlopen):
            ret = self.request.call_service(METHOD_NAME, **METHOD_PARAMS)
            self.assertIsInstance(ret, minidom.Document)
                
        self.assertTrue(mock_urlopen.called)
        call_args, call_kwargs = mock_urlopen.call_args
        self.assertEqual(call_kwargs, {})
        self.assertEqual(len(call_args), 2)
        # call_args[0] is the URL
        self.assertEqual(call_args[0], self.config.serviceurl)
        # call_args[1] is the string result of urlencoding the parameters
        self.assertIn('appid=%s' % self.config.appid, call_args[1])
        self.assertIn('method=%s' % METHOD_NAME, call_args[1])
        for key in METHOD_PARAMS:
            self.assertIn('%s=%s' % (key, METHOD_PARAMS[key]), call_args[1])
