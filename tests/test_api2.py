"""This is the test module for the Localrouter class, 
made by Marwan Amrhar & Yahia Noeman & Ayoub Bouazza & Sajeed Bouzziane.
It covers the functions:
    API.__init__
    ModuleSingleton.__call__"""

import unittest
from hug.api import API

class MockModule:
    __name__ = "mock_module"
    __doc__ = "This is a mock module"

class TestAPIInit(unittest.TestCase):
    def test_api_init_with_module(self):
        """Test API initialization with module"""
        module = MockModule()
        api = API(module=module)
        
        self.assertEqual(api.module, module)
        self.assertEqual(api.name, "mock_module")
        self.assertEqual(api.doc, "This is a mock module")
        self.assertFalse(api.started)
        self.assertFalse(api.cli_error_exit_codes)
        self.assertFalse(api.future)

    def test_api_init_without_module(self):
        """Test API initialization without module"""
        name = "test_name"
        doc = "This is a test doc"
        cli_error_exit_codes = True
        future = True

        api = API(name=name, doc=doc, cli_error_exit_codes=cli_error_exit_codes, future=future)
        
        self.assertIsNone(api.module)
        self.assertEqual(api.name, name)
        self.assertEqual(api.doc, doc)
        self.assertFalse(api.started)
        self.assertTrue(api.cli_error_exit_codes)
        self.assertTrue(api.future)

    def test_api_init_with_partial_module_attributes(self):
        """Test API initialization with module and partial attributes"""
        module = MockModule()
        name = "custom_name"
        doc = "Custom documentation"

        api = API(module=module, name=name, doc=doc)
        
        self.assertEqual(api.module, module)
        self.assertEqual(api.name, name)
        self.assertEqual(api.doc, doc)
        self.assertFalse(api.started)
        self.assertFalse(api.cli_error_exit_codes)
        self.assertFalse(api.future)

    def test_api_init_with_empty_module(self):
        """Test API initialization with empty module attributes"""
        class EmptyModule:
            __name__ = None
            __doc__ = None
        
        module = EmptyModule()
        api = API(module=module)
        
        self.assertEqual(api.module, module)
        self.assertEqual(api.name, "")
        self.assertEqual(api.doc, "")
        self.assertFalse(api.started)
        self.assertFalse(api.cli_error_exit_codes)
        self.assertFalse(api.future)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAPIInit))
    return suite

if __name__ == "__main__":
    runner = unittest.TextTestRunner()
    runner.run(test_suite())
