import functools

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import settings

def network_test(f):
    """
    decorator for any test that uses the network, such as to make an actual API
    call. If settings.ENABLE_NETWORK_TESTS == False, this decorator will cause
    those tests to be skipped.
    """
    @functools.wraps(f)
    def decorator(*args, **kwargs):
        if settings.ENABLE_NETWORK_TESTS:
            return f(*args, **kwargs)
        else:
            instance = args[0]
            assert isinstance(instance, unittest.TestCase)
            instance.skipTest('Network tests are not enabled.')
    return decorator
